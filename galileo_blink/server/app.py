"""The web layer: a thin HTTP API over the engine, plus the built interface as static files.

It holds no astronomy. Every route either asks the engine a question or serves a file the
engine wrote.
"""
from __future__ import annotations

import io
from pathlib import Path

import numpy as np
from fastapi import FastAPI, HTTPException, Query
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

WEB_DIST = Path(__file__).resolve().parents[2] / "web" / "dist"
SAFE_FILE = {".png": "image/png", ".json": "application/json"}


def create_app(builder: Builder | None = None) -> FastAPI:
    app = FastAPI(title="Galileo Blink", version="0.1.0", docs_url="/api/docs", redoc_url=None)
    app.add_middleware(GZipMiddleware, minimum_size=1024)
    builder = builder or Builder()
    app.state.builder = builder

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

    @app.get("/api/resolve")
    def resolve(q: str = Query(..., max_length=200)):
        """Coordinates or a name -> a place in the sky."""
        p = coords.resolve(q)
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
    def open_view(ra: float | None = None, dec: float | None = None,
                  size: float = C.FIELD_DEFAULT_DEG, target: str | None = None):
        """Open (and if needed start building) the view of a place. Poll /api/view/{key}."""
        return _ensure(_request(ra, dec, size, target))

    def _ensure(req):
        try:
            return builder.ensure(req)
        except Busy:
            return JSONResponse({"error": "Many views are being built right now. Please try "
                                          "again in a moment.", "error_kind": "busy"},
                                status_code=503)

    @app.get("/api/visit")
    def open_visit(ra: float = Query(..., ge=0, le=360), dec: float = Query(..., ge=-90, le=90),
                   size: float = Query(0.2, ge=C.FIELD_MIN_DEG, le=C.FIELD_MAX_DEG),
                   camera: int | None = Query(None, ge=1, le=6)):
        """Open the asteroid view of a place: one visit, moment by moment, searched for movers.
        Poll /api/view/{key} like any other view."""
        return _ensure(VisitRequest(ra=round(ra % 360.0, 5), dec=round(dec, 5),
                                    size_deg=round(size, 3), camera=camera))

    @app.get("/api/asteroid")
    def open_asteroid(name: str = Query(..., max_length=60)):
        """Find a named asteroid in SPHEREx's photos and open the visit where it is best seen."""
        v = asteroids.find_asteroid(name)
        status = _ensure(VisitRequest(ra=v.ra, dec=v.dec, size_deg=v.size_deg, camera=v.camera,
                                      mjd_start=round(v.mjd_start, 4), mjd_end=round(v.mjd_end, 4),
                                      label=v.name))
        if isinstance(status, dict):
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
            return cube.quick_spectrum(ra, dec)
        except ServiceDown:
            raise
        except Exception as e:                  # noqa: BLE001 - an unexpected tile layout
            raise ServiceDown(cube.SERVICE, type(e).__name__) from e

    @app.get("/api/about")
    def about():
        """The numbers and limits the interface states out loud."""
        return dict(
            pixel_arcsec=C.PIXEL_ARCSEC, cameras={str(k): v for k, v in C.CAMERA_BANDS_MICRON.items()},
            field=dict(min=C.FIELD_MIN_DEG, max=C.FIELD_MAX_DEG, default=C.FIELD_DEFAULT_DEG),
            flags=engine_flags.describe(), mask_bits=list(C.MASK_BITS),
            min_marked_motion=C.MIN_PM_MARK_ARCSEC_YR, engine=C.ENGINE_VERSION)

    if WEB_DIST.is_dir():
        app.mount("/assets", StaticFiles(directory=WEB_DIST / "assets"), name="assets")

        @app.get("/{path:path}", include_in_schema=False)
        def spa(path: str):
            """The interface: a real file if one exists, otherwise the single-page app."""
            candidate = (WEB_DIST / path).resolve()
            if path and candidate.is_file() and WEB_DIST.resolve() in candidate.parents:
                return FileResponse(candidate)
            return FileResponse(WEB_DIST / "index.html", headers={"Cache-Control": "no-cache"})

    return app


app = create_app()
