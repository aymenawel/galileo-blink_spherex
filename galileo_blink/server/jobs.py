"""Building a view takes seconds to a minute, so it runs in the background and the browser
polls. This module owns that queue: one build per view at a time, a small worker pool so NASA's
servers are never flooded, and honest states (building, ready, failed and whose fault).
"""
from __future__ import annotations

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
JOB_MAX_RUN_S = 600.0
PREBUILT_DIR = Path(__file__).resolve().parents[2] / "prebuilt"


@dataclass
class Job:
    key: str
    state: str = "queued"             # queued | building | ready | failed
    stage: str = "Waiting for a free builder"
    fraction: float = 0.0
    error: str | None = None
    error_kind: str | None = None     # "request" (the visitor's input), "service" (NASA/catalogue), "internal"
    started: float = field(default_factory=time.time)

    def public(self) -> dict:
        return dict(key=self.key, state=self.state, stage=self.stage,
                    fraction=round(self.fraction, 3), error=self.error, error_kind=self.error_kind,
                    seconds=round(time.time() - self.started, 1))


def build_any(req, progress):
    """Build whichever kind of view the request asks for."""
    if isinstance(req, VisitRequest):
        return build_visit(req, progress)
    return build_view(req, progress)


class Busy(Exception):
    """Too many builds are already waiting."""


class Builder:
    def __init__(self, build=build_any):
        self._build = build
        self._pool = ThreadPoolExecutor(MAX_BUILDS_AT_ONCE, thread_name_prefix="build")
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()

    # ---------------------------------------------------------------- finished views on disk
    @staticmethod
    def view_path(key: str) -> Path | None:
        """Folder holding a finished view: shipped with the site (prebuilt) or built here."""
        for root in (cache_dir() / "views", PREBUILT_DIR):
            if (root / key / "view.json").is_file():
                return root / key
        return None

    def load(self, key: str) -> dict | None:
        """A finished view, unless it was built during an outage long enough ago to retry."""
        path = self.view_path(key)
        if path is None:
            return None
        view = read_json(path / "view.json")
        if view is None or view.get("engine") != C.ENGINE_VERSION:
            return None
        retryable = [d for d in view.get("degraded", []) if d != "photo_list"]
        if retryable and path.parent != PREBUILT_DIR:
            if time.time() - (path / "view.json").stat().st_mtime > C.DEGRADED_RETRY_S:
                return None
        return view

    # ---------------------------------------------------------------- building
    def ensure(self, req: ViewRequest | VisitRequest) -> dict:
        """Make sure the view exists or is on its way. Returns its public state."""
        key = req.key
        if self.load(key) is not None:
            return dict(key=key, state="ready")
        with self._lock:
            job = self._jobs.get(key)
            if job and job.state in ("queued", "building"):
                return job.public()
            waiting = sum(1 for j in self._jobs.values() if j.state == "queued")
            if waiting >= MAX_WAITING:
                raise Busy()
            job = self._jobs[key] = Job(key=key)
        self._pool.submit(self._run, job, req)
        return job.public()

    def status(self, key: str) -> dict | None:
        with self._lock:
            job = self._jobs.get(key)
        if job and job.state in ("queued", "building"):
            if time.time() - job.started > JOB_MAX_RUN_S:
                job.state, job.error_kind = "failed", "internal"
                job.error = "This build took too long and was stopped. Please try again."
            return job.public()
        if self.load(key) is not None:
            return dict(key=key, state="ready")
        return job.public() if job else None

    def _run(self, job: Job, req: ViewRequest | VisitRequest) -> None:
        job.state, job.stage = "building", "Starting"

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
        except Exception:                       # noqa: BLE001 - report, never crash the worker
            traceback.print_exc()
            job.state, job.error_kind = "failed", "internal"
            job.error = "Something went wrong inside Galileo Blink while building this view."
