"""The engine's only door to the network: every request has a deadline and polite retries."""
from __future__ import annotations

import threading
import time

import requests
from requests.adapters import HTTPAdapter

from .. import constants as C
from ..errors import ServiceDown

_local = threading.local()
MAX_TIMEOUTS_IN_A_ROW = 2
"""A request that times out this many times running is given up: with a 45 s deadline, twenty
patient retries would otherwise hold a build for half an hour."""


def session() -> requests.Session:
    """One pooled session per thread (requests sessions are not thread-safe)."""
    s = getattr(_local, "session", None)
    if s is None:
        s = requests.Session()
        s.headers["User-Agent"] = C.USER_AGENT
        adapter = HTTPAdapter(pool_connections=8, pool_maxsize=32)
        s.mount("https://", adapter)
        s.mount("http://", adapter)
        _local.session = s
    return s


def request(method: str, url: str, *, service: str, timeout: float = C.HTTP_TIMEOUT_S,
            retries: int | None = None, backoff: tuple[float, ...] = C.BUSY_BACKOFF_S,
            **kwargs) -> requests.Response:
    """One request with a deadline. "Busy" answers and network errors are retried with
    backoff; any other HTTP error is raised at once. Failure raises ServiceDown(service).

    A refusal is instant, so it is worth many retries; a timeout costs the whole deadline, so
    after MAX_TIMEOUTS_IN_A_ROW of them the service is taken to be down."""
    last, timeouts = "", 0
    retries = len(backoff) if retries is None else retries
    for attempt in range(retries + 1):
        try:
            r = session().request(method, url, timeout=timeout, **kwargs)
        except requests.Timeout as e:
            last, timeouts = type(e).__name__, timeouts + 1
            if timeouts >= MAX_TIMEOUTS_IN_A_ROW:
                raise ServiceDown(service, last, timed_out=True) from None
        except requests.RequestException as e:
            last, timeouts = type(e).__name__, 0
        else:
            if r.status_code < 400:
                return r
            last, timeouts = f"HTTP {r.status_code}", 0
            if r.status_code not in C.BUSY_STATUS:
                break
        if attempt < retries:
            time.sleep(backoff[min(attempt, len(backoff) - 1)])
    raise ServiceDown(service, last, timed_out=timeouts > 0)


def get(url: str, *, service: str, **kwargs) -> requests.Response:
    return request("GET", url, service=service, **kwargs)


def read_range(url: str, start: int, end: int, *, service: str, retries: int = 2) -> bytes:
    """Bytes start..end (inclusive) of a remote file."""
    r = get(url, service=service, retries=retries, headers={"Range": f"bytes={start}-{end}"})
    if r.status_code != 206:
        raise ServiceDown(service, "it ignored a partial-read request")
    return r.content
