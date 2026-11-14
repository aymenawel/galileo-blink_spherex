"""The engine's own error types, so the web layer can tell whose fault a failure is."""


class UserError(ValueError):
    """Something wrong with what was asked for, worded for the person who asked (HTTP 400)."""


class ServiceDown(RuntimeError):
    """A NASA or catalogue service did not answer usefully (HTTP 502). `service` names it in
    plain words, e.g. "NASA's image archive (IRSA)"."""

    def __init__(self, service: str, detail: str = ""):
        super().__init__(f"{service} did not answer" + (f": {detail}" if detail else ""))
        self.service = service
        self.detail = detail


class NoCoverage(UserError):
    """SPHEREx has no usable photos of this place (yet)."""
