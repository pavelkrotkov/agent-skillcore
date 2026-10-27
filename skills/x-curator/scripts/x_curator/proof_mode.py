"""Explicit maintenance can force original byte-level proof replay."""
from contextlib import contextmanager
from contextvars import ContextVar

class MaintenanceRequired(RuntimeError):
    pass


FULL=ContextVar('full_proof_audit',default=False)


@contextmanager
def audit(enabled=True):
    token=FULL.set(enabled)
    try:
        yield
    finally:
        FULL.reset(token)
