"""The web layer: a thin HTTP API over the engine, plus the built interface as static files.

It holds no astronomy. Every route either asks the engine a question or serves a file the
engine wrote.
"""
from __future__ import annotations

import json
import mimetypes
import threading
from pathlib import Path

import numpy as np
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from ..engine import constants as C
from ..engine import flags as engine_flags
from ..engine.errors import ServiceDown, UserError
from ..engine.image import render
from ..engine.image.stack import change_map, combine
from ..engine.looks.build import ViewRequest, target_request
from ..engine.sky import asteroids, coords, targets
from ..engine.spectrum import cube
from ..engine.visit.build import VisitRequest
from .jobs import Builder, Busy

# Some systems (Windows among them) do not know the web-font type and send it as raw bytes.
mimetypes.add_type("font/woff2", ".woff2")

WEB_DIST = Path(__file__).resolve().parents[2] / "web" / "dist"
ASTEROID_EXAMPLES = Path(__file__).resolve().parents[2] / "data" / "asteroid_examples.json"
SAFE_FILE = {".png": "image/png", ".json": "application/json"}
# Lookups that wait on an outside service (names, asteroids, the all-sky cube) share this many
# slots, so a burst of them can never use up the threads that serve the pages and pictures.
SLOW_LOOKUPS_AT_ONCE = 8
# The page loads only its own scripts, styles, fonts and pictures, and talks only to this server.
CONTENT_SECURITY_POLICY = (
    "default-src 'self'; img-src 'self' data: blob:; style-src 'self' 'unsafe-inline'; "
    "font-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'self'; "
    "frame-ancestors 'none'; form-action 'self'")
GIF_CREDIT = "SPHEREx data: NASA/JPL-Caltech · galileoblink.earth"
SAFETY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Strict-Transport-Security": "max-age=31536000",
}


class BuiltFiles(StaticFiles):
    """The interface's built scripts, styles and fonts. Their names carry a hash of their
    content, so a browser may keep them for good: a new build has new names."""

    async def get_response(self, path, scope):
        response = await super().get_response(path, scope)
        if response.status_code == 200:
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        return response


class Limiter:
    """Lets a fixed number of slow jobs run at once and turns the rest away at the door."""

    def __init__(self, slots: int):
        self._slots = threading.Semaphore(slots)

    def run(self, work, *args):
        if not self._slots.acquire(blocking=False):
            raise Busy()
        try:
            return work(*args)
        finally:
            self._slots.release()


def _visitor(request: Request) -> str:
    """Who a request came from, for the per-visitor limit. Google's front end appends the
    visitor's own address to X-Forwarded-For, so the last entry is the real one; anything
    before it is whatever the sender chose to write and is ignored. (Checked on the live
    site: a made-up entry arrives in front of the real address, never after it.)"""
    hops = [hop.strip() for hop in request.headers.get("x-forwarded-for", "").split(",") if hop.strip()]
    return hops[-1] if hops else (request.client.host if request.client else "")


def _example_request(e: dict) -> VisitRequest:
    return VisitRequest(ra=e["ra"], dec=e["dec"], size_deg=e["size_deg"], camera=e["camera"],
                        mjd_start=e["mjd_start"], mjd_end=e["mjd_end"], label=e["name"])


def create_app(builder: Builder | None = None) -> FastAPI:
    app = FastAPI(title="Galileo Blink", version="0.1.0", docs_url="/api/docs", redoc_url=None)
    app.add_middleware(GZipMiddleware, minimum_size=1024)
    builder = builder or Builder()
    app.state.builder = builder
    app.state.lookups = Limiter(SLOW_LOOKUPS_AT_ONCE)

    @app.middleware("http")
    async def _safety_headers(request: Request, call_next):
        response = await call_next(request)
        for name, value in SAFETY_HEADERS.items():
            response.headers.setdefault(name, value)
        if not request.url.path.startswith("/api/docs"):    # the API explorer loads from a CDN
            response.headers.setdefault("Content-Security-Policy", CONTENT_SECURITY_POLICY)
        return response

    @app.exception_handler(Busy)
    async def _busy(_, exc: Busy):
        return JSONResponse({"error": "Galileo Blink is very busy right now. Please try again in "
                                      "a moment.", "error_kind": "busy"}, status_code=503)

    @app.exception_handler(UserError)
    async def _user_error(_, exc: UserError):
        return JSONResponse({"error": str(exc), "error_kind": "request"}, status_code=400)

    @app.exception_handler(ServiceDown)
    async def _service_down(_, exc: ServiceDown):
        return JSONResponse({"error": f"{exc.service} did not answer just now. Please try again "
                                      "in a minute.", "error_kind": "service"}, status_code=502)

    @app.get("/api/health")
    def health():
        return {"ok": True, "engine": C.ENGINE_VERSION}

    @app.get("/api/targets")
    def list_targets():
        """NASA's five test targets, each with the key of its ready-made view."""
        out = []
        for t in targets.targets():
            req = target_request(t.id)
            out.append(dict(id=t.id, name=t.name, kind=t.kind, blurb=t.blurb, key=req.key,
                            ra=req.ra, dec=req.dec, pm=round(t.mover.pm_total, 2),
                            ready=builder.load(req.key) is not None))
        return out

    @app.get("/api/asteroids")
    def list_asteroids():
        """Ready-made asteroid examples: real asteroids crossing real SPHEREx visits."""
        out = []
        for e in json.loads(ASTEROID_EXAMPLES.read_text(encoding="utf8")):
            req = _example_request(e)
            out.append(dict(id=e["id"], name=e["name"], blurb=e["blurb"], vmag=e["vmag"],
                            camera=e["camera"], key=req.key, ready=builder.load(req.key) is not None))
        return out

    @app.get("/api/asteroids/{example_id}")
    def open_example(example_id: str, request: Request):
        for e in json.loads(ASTEROID_EXAMPLES.read_text(encoding="utf8")):
            if e["id"] == example_id:
                return builder.ensure(_example_request(e), _visitor(request))
        raise HTTPException(404, "No such asteroid example.")

    @app.get("/api/resolve")
    def resolve(q: str = Query(..., max_length=200)):
        """Coordinates or a name -> a place in the sky."""
        p = app.state.lookups.run(coords.resolve, q)
        return dict(ra=p.ra, dec=p.dec, label=p.label, kind=p.kind, target_id=p.target_id,
                    moved_arcmin=p.moved_arcmin, follows=p.follows)

    def _request(ra, dec, size, target) -> ViewRequest:
        if target:
            if targets.by_id(target) is None:
                raise UserError(f"There is no test target called “{target}”.")
            return target_request(target)
        if ra is None or dec is None:
            raise UserError("A view needs a right ascension and a declination, or a target.")
        if not (0 <= ra <= 360 and -90 <= dec <= 90):
            raise UserError("Right ascension must be 0-360 degrees and declination -90 to +90.")
        if not (C.FIELD_MIN_DEG <= size <= C.FIELD_MAX_DEG):
            raise UserError(f"The field of view must be between {C.FIELD_MIN_DEG} and "
                            f"{C.FIELD_MAX_DEG} degrees.")
        return ViewRequest(ra=round(ra % 360.0, 5), dec=round(dec, 5), size_deg=round(size, 3))

    @app.get("/api/view")
    def open_view(request: Request, ra: float | None = None, dec: float | None = None,
                  size: float = C.FIELD_DEFAULT_DEG, target: str | None = None):
        """Open (and if needed start building) the view of a place. Poll /api/view/{key}."""
        return builder.ensure(_request(ra, dec, size, target), _visitor(request))

    @app.get("/api/visit")
    def open_visit(request: Request,
                   ra: float = Query(..., ge=0, le=360), dec: float = Query(..., ge=-90, le=90),
                   size: float = Query(0.2, ge=C.FIELD_MIN_DEG, le=C.FIELD_MAX_DEG),
                   camera: int | None = Query(None, ge=1, le=6)):
        """Open the asteroid view of a place: one visit, moment by moment, searched for movers.
        Poll /api/view/{key} like any other view."""
        return builder.ensure(VisitRequest(ra=round(ra % 360.0, 5), dec=round(dec, 5),
                                           size_deg=round(size, 3), camera=camera), _visitor(request))

    @app.get("/api/asteroid")
    def open_asteroid(request: Request, name: str = Query(..., max_length=60)):
        """Find a named asteroid in SPHEREx's photos and open the visit where it is best seen."""
        v = app.state.lookups.run(asteroids.find_asteroid, name)
        status = builder.ensure(VisitRequest(ra=v.ra, dec=v.dec, size_deg=v.size_deg, camera=v.camera,
                                             mjd_start=round(v.mjd_start, 4),
                                             mjd_end=round(v.mjd_end, 4), label=v.name),
                                _visitor(request))
        status["asteroid"] = dict(name=v.name, vmag=v.vmag, camera=v.camera,
                                  n_moments=v.n_moments, ra=v.ra, dec=v.dec)
        return status

    @app.get("/api/view/{key}")
    def view_status(key: str):
        status = builder.status(key)
        if status is None:
            raise HTTPException(404, "No such view. Open it with /api/view?ra=..&dec=..")
        if status["state"] == "ready":
            status["view"] = builder.load(key)
        return status

    @app.get("/files/{key}/{name}")
    def view_file(key: str, name: str):
        """A picture belonging to a view."""
        folder = builder.view_path(key)
        suffix = Path(name).suffix
        if folder is None or suffix not in SAFE_FILE or Path(name).name != name:
            raise HTTPException(404)
        path = folder / name
        if not path.is_file():
            raise HTTPException(404)
        # pictures are rewritten when a view is rebuilt, so the browser must revalidate
        return FileResponse(path, media_type=SAFE_FILE[suffix],
                            headers={"Cache-Control": "no-cache"})

    @app.get("/api/view/{key}/compare")
    def compare(key: str, camera: int = Query(..., ge=1, le=6), a: str = "all", b: str = "all",
                op: str = Query("subtract", pattern="^(subtract|add)$")):
        """Subtract season `b` from season `a` (a change map), or add them, for one camera.
        `a` and `b` are season numbers or "all" (every season combined)."""
        folder = builder.view_path(key)
        if folder is None or not (folder / "stacks.npz").is_file():
            raise HTTPException(404)
        with np.load(folder / "stacks.npz") as stacks:
            def get(which: str):
                name = f"c{camera}_all" if which == "all" else f"c{camera}_s{int(which)}"
                if name not in stacks:
                    raise UserError("That camera has no photos for that season.")
                return stacks[name]
            try:
                first, second, reference = get(a), get(b), get("all")
            except ValueError:
                raise UserError("Seasons are numbers, or “all”.") from None
        if op == "subtract":
            png = render.change_png(change_map(first, second, reference))
        else:
            total = combine([first, second])
            limits = render.display_limits(total)
            if limits is None:
                raise UserError("There is no data to add for that camera.")
            png = render.gray_png(render.stretch(total, *limits))
        return Response(png, media_type="image/png", headers={"Cache-Control": "no-cache"})

    @app.get("/api/spectrum")
    def spectrum(ra: float = Query(..., ge=0, le=360), dec: float = Query(..., ge=-90, le=90)):
        """A quick 102-colour spectrum of any place, from NASA's all-sky SPHEREx cube."""
        try:
            return app.state.lookups.run(cube.quick_spectrum, ra, dec)
        except (ServiceDown, Busy):
            raise
        except Exception as e:                  # noqa: BLE001 - an unexpected tile layout
            raise ServiceDown(cube.SERVICE, type(e).__name__) from e

    @app.get("/api/view/{key}/blink.gif")
    def blink_gif(key: str, camera: int = Query(..., ge=1, le=6), layer: str = Query("photo", pattern="^(photo|change)$"),
                  ms: int = Query(700, ge=150, le=3000)):
        """The blink of one camera as an animated GIF, to save or share."""
        found = builder.find(key)
        if found is None:
            raise HTTPException(404)
        folder, view = found
        looks = (view.get("cameras", {}).get(str(camera)) or {}).get("looks") or []
        labels = {s["index"]: s["label"] for s in view.get("seasons", [])}
        pictures, captions = [], []
        for look in looks:
            name = look.get("change") if layer == "change" and look.get("change") else look.get("png")
            if name and (folder / name).is_file():
                pictures.append((folder / name).read_bytes())
                captions.append(f"{labels.get(look['season'], '')}  ·  camera {camera}")
        if not pictures:
            raise UserError("That camera has no pictures to animate.")
        name = (view.get("target") or {}).get("name") or view.get("label") or "sky"
        # a header can only carry plain letters, so anything else in the name becomes a dash
        slug = "".join(c if c.isascii() and c.isalnum() else "-" for c in name.lower()).strip("-") or "sky"
        gif = render.blink_gif(pictures, captions, GIF_CREDIT, ms)
        return Response(gif, media_type="image/gif", headers={
            "Content-Disposition": f'attachment; filename="galileo-blink-{slug}-camera{camera}.gif"',
            "Cache-Control": "no-cache"})

    @app.get("/api/about")
    def about():
        """The numbers and limits the interface states out loud."""
        return dict(
            pixel_arcsec=C.PIXEL_ARCSEC, cameras={str(k): v for k, v in C.CAMERA_BANDS_MICRON.items()},
            field=dict(min=C.FIELD_MIN_DEG, max=C.FIELD_MAX_DEG, default=C.FIELD_DEFAULT_DEG),
            flags=engine_flags.describe(), mask_bits=list(C.MASK_BITS),
            min_marked_motion=C.MIN_PM_MARK_ARCSEC_YR, engine=C.ENGINE_VERSION)

    if WEB_DIST.is_dir():
        app.mount("/assets", BuiltFiles(directory=WEB_DIST / "assets"), name="assets")

        @app.api_route("/{path:path}", methods=["GET", "HEAD"], include_in_schema=False)
        def spa(path: str):
            """The interface: a real file if one exists, otherwise the single-page app."""
            if path.startswith(("api/", "files/")):
                raise HTTPException(404)        # a wrong data address is not a page
            candidate = (WEB_DIST / path).resolve()
            if path and candidate.is_file() and WEB_DIST.resolve() in candidate.parents:
                return FileResponse(candidate)
            return FileResponse(WEB_DIST / "index.html", headers={"Cache-Control": "no-cache"})

    return app


app = create_app()
