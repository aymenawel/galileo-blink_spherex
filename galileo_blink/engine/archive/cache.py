"""Where the engine keeps what it has already fetched or built, and safe ways to write it."""
from __future__ import annotations

import itertools
import json
import os
import threading
import time
from pathlib import Path

_seq = itertools.count()
_locks: dict[str, threading.Lock] = {}
_locks_guard = threading.Lock()


def cache_dir() -> Path:
    """Root of the cache: $GALILEO_BLINK_CACHE, or ./cache beside the repository."""
    root = os.environ.get("GALILEO_BLINK_CACHE")
    path = Path(root) if root else Path(__file__).resolve().parents[3] / "cache"
    path.mkdir(parents=True, exist_ok=True)
    return path


def lock_for(key: str) -> threading.Lock:
    """One lock per name, so two builds never fetch or write the same thing at once."""
    with _locks_guard:
        return _locks.setdefault(key, threading.Lock())


def _unique_tmp(path: Path) -> Path:
    return path.with_name(f"{path.name}.{os.getpid()}.{threading.get_ident()}.{next(_seq)}.tmp")


def atomic_write(path: Path, data: bytes) -> None:
    """Write via a temp file unique to this writer, then rename: a crash or a second writer
    can never leave a half-written file behind."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = _unique_tmp(path)
    try:
        tmp.write_bytes(data)
        for attempt in range(5):                # on Windows a reader can briefly hold the target
            try:
                os.replace(tmp, path)
                return
            except PermissionError:
                if attempt == 4:
                    raise
                time.sleep(0.05 * (attempt + 1))
    finally:
        tmp.unlink(missing_ok=True)


def write_json(path: Path, obj) -> None:
    atomic_write(path, json.dumps(obj, separators=(",", ":")).encode("utf8"))


def read_json(path: Path):
    """The parsed file, or None if it is missing or corrupt (a corrupt file is removed so it
    is rebuilt; a file that is merely locked is left alone)."""
    try:
        return json.loads(path.read_text(encoding="utf8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        path.unlink(missing_ok=True)
        return None
    except OSError:
        return None
