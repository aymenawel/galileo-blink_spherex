"""Building a view takes seconds to a minute, so it runs in the background and the browser
polls. This module owns that queue: one build per view at a time, a small worker pool so NASA's
servers are never flooded, and honest states (building, ready, failed and whose fault).
"""
from __future__ import annotations

import os
import re
import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

from ..engine import constants as C
from ..engine.archive.cache import cache_dir, read_json, trim
from ..engine.errors import ServiceDown, UserError
from ..engine.looks.build import ViewRequest, build_view
from ..engine.visit.build import VisitRequest, build_visit

MAX_BUILDS_AT_ONCE = 2
MAX_WAITING = 8
# One visitor may have this many views on their way at once, so nobody can fill the queue alone.
MAX_PER_VISITOR = 3
JOB_MAX_RUN_S = 600.0
JOB_MAX_WAIT_S = 1200.0           # a build still waiting for a builder after this long is dropped
TOO_SLOW = ("NASA's archive may be slow right now, so this view took too long and was stopped. "
            "This is not your fault: please try again in a few minutes.")
PREBUILT_DIR = Path(__file__).resolve().parents[2] / "prebuilt"
# A view's key is made by the engine from letters, digits and dashes; anything else is not a key.
VIEW_KEY = re.compile(r"[A-Za-z0-9-]{1,64}")


@dataclass
class Job:
    key: str
    state: str = "queued"             # queued | building | ready | failed
    stage: str = "Waiting for a free builder"
    fraction: float = 0.0
    error: str | None = None
    error_kind: str | None = None     # "request" (the visitor's input), "service" (NASA/catalogue), "internal"
    queued: float = field(default_factory=time.time)
    started: float | None = None      # when a builder took it (None while it waits)
    owner: str = ""                   # who asked first (an address), for the per-visitor limit

    def public(self) -> dict:
        return dict(key=self.key, state=self.state, stage=self.stage,
                    fraction=round(self.fraction, 3), error=self.error, error_kind=self.error_kind,
                    seconds=round(time.time() - self.queued, 1))

    def too_slow(self) -> bool:
        now = time.time()
        if self.started is None:
            return now - self.queued > JOB_MAX_WAIT_S
        return now - self.started > JOB_MAX_RUN_S


def build_any(req, progress):
    """Build whichever kind of view the request asks for."""
    if isinstance(req, VisitRequest):
        return build_visit(req, progress)
    return build_view(req, progress)


class Busy(Exception):
    """Too many builds are already waiting, or too many lookups are already running."""


class Builder:
    def __init__(self, build=build_any):
        self._build = build
        self._pool = ThreadPoolExecutor(MAX_BUILDS_AT_ONCE, thread_name_prefix="build")
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()

    # ---------------------------------------------------------------- finished views on disk
    @staticmethod
    def find(key: str) -> tuple[Path, dict] | None:
        """(folder, view) of the first usable finished view: built here, or shipped with the
        site. A copy from an older engine, or one built during an outage long enough ago to
        retry, is passed over, so a stale copy in one place never hides a good one in the other."""
        if not VIEW_KEY.fullmatch(key):
            return None
        for root in (cache_dir() / "views", PREBUILT_DIR):
            folder = root / key
            if not (folder / "view.json").is_file():
                continue
            view = read_json(folder / "view.json")
            if view is None or view.get("engine") != C.ENGINE_VERSION:
                continue
            retryable = [d for d in view.get("degraded", []) if d != "photo_list"]
            if retryable and root != PREBUILT_DIR:
                if time.time() - (folder / "view.json").stat().st_mtime > C.DEGRADED_RETRY_S:
                    continue
            return folder, view
        return None

    def view_path(self, key: str) -> Path | None:
        """Folder holding a finished view's pictures."""
        found = self.find(key)
        return found[0] if found else None

    def load(self, key: str) -> dict | None:
        """A finished view's description."""
        found = self.find(key)
        return found[1] if found else None

    # ---------------------------------------------------------------- building
    def ensure(self, req: ViewRequest | VisitRequest, owner: str = "") -> dict:
        """Make sure the view exists or is on its way. Returns its public state. `owner` says
        who is asking; one owner can only have MAX_PER_VISITOR views on their way at once."""
        key = req.key
        if self.load(key) is not None:
            return dict(key=key, state="ready")
        with self._lock:
            job = self._jobs.get(key)
            if job and job.state in ("queued", "building"):
                return job.public()
            unfinished = [j for j in self._jobs.values() if j.state in ("queued", "building")]
            if sum(1 for j in unfinished if j.state == "queued") >= MAX_WAITING:
                raise Busy()
            if owner and sum(1 for j in unfinished if j.owner == owner) >= MAX_PER_VISITOR:
                raise Busy()
            job = self._jobs[key] = Job(key=key, owner=owner)
        self._pool.submit(self._run, job, req)
        return job.public()

    def status(self, key: str) -> dict | None:
        with self._lock:
            job = self._jobs.get(key)
        if job and job.state in ("queued", "building"):
            if not job.too_slow():
                return job.public()
            job.state, job.error_kind, job.error = "failed", "service", TOO_SLOW
            if self._keep_old_view(key):
                return dict(key=key, state="ready")
            return job.public()
        if self.load(key) is not None:
            return dict(key=key, state="ready")
        return job.public() if job else None

    @staticmethod
    def _keep_old_view(key: str) -> bool:
        """After a rebuild failed on NASA's side, keep serving the view built during the
        earlier outage (it says what was missing) for another DEGRADED_RETRY_S, rather than
        replace a usable view with an error."""
        if not VIEW_KEY.fullmatch(key):
            return False
        path = cache_dir() / "views" / key / "view.json"
        view = read_json(path) if path.is_file() else None
        if not view or view.get("engine") != C.ENGINE_VERSION:
            return False
        try:
            os.utime(path)
        except OSError:
            return False
        return True

    def _run(self, job: Job, req: ViewRequest | VisitRequest) -> None:
        if job.state != "queued":
            return                              # given up on while it waited
        job.state, job.stage, job.started = "building", "Starting", time.time()

        def progress(stage: str, fraction: float) -> None:
            job.stage, job.fraction = stage, fraction

        try:
            self._build(req, progress)
            job.state, job.fraction = "ready", 1.0
            trim(cache_dir() / "photos", C.CACHE_PHOTOS_MAX_BYTES)
            trim(cache_dir() / "views", C.CACHE_VIEWS_MAX_BYTES)
        except UserError as e:
            job.state, job.error, job.error_kind = "failed", str(e), "request"
        except ServiceDown as e:
            job.state, job.error_kind = "failed", "service"
            job.error = (f"{e.service} did not answer just now. This is on NASA's side, not "
                         "yours: please try again in a minute.")
            self._keep_old_view(job.key)
        except Exception:                       # noqa: BLE001 - report, never crash the worker
            traceback.print_exc()
            job.state, job.error_kind = "failed", "internal"
            job.error = "Something went wrong inside Galileo Blink while building this view."
