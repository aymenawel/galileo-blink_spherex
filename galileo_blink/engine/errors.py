"""The engine's own error types, so the web layer can tell whose fault a failure is."""


class UserError(ValueError):
    """Something wrong with what was asked for, worded for the person who asked (HTTP 400)."""


class ServiceDown(RuntimeError):
    """A NASA or catalogue service did not answer usefully (HTTP 502). `service` names it in
    plain words, e.g. "NASA's image archive (IRSA)". `timed_out` is True when the service
    stopped answering altogether rather than refusing."""

    def __init__(self, service: str, detail: str = "", timed_out: bool = False):
        super().__init__(f"{service} did not answer" + (f": {detail}" if detail else ""))
        self.service = service
        self.detail = detail
        self.timed_out = timed_out


class NoCoverage(UserError):
    """SPHEREx has no usable photos of this place (yet)."""
