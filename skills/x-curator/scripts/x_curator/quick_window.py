"""Reserve the final forty seconds for correction without extending the check."""
import time
import json
from contextlib import contextmanager
from functools import wraps

from . import quick_store
from .deadlines import until, DeadlineExceeded

READ_CLOSED = 'quick read window closed; validate a minimal draft using already observed evidence now'


def require_phase(db, token, name):
    row = db.execute("SELECT input FROM executions WHERE token=? AND role IN ('factcheck','factcheck_evidence') AND finished IS NULL ORDER BY started DESC,id DESC LIMIT 1", (token,)).fetchone()
    phase = json.loads(row['input']).get('phase', {}).get('name') if row else None
    if (phase == 'final' and name != 'validate') or (phase == 'evidence' and name == 'validate'):
        raise ValueError('tool unavailable in the controller-owned ' + phase + ' phase')


@contextmanager
def window(db, token):
    row = quick_store.active(db, token)
    limit = row['deadline'] if row.get('policy') else min(row['deadline'], row['started'] + 80)
    if time.time() >= limit:
        raise ValueError(READ_CLOSED)
    try:
        with until(limit):
            yield
    except DeadlineExceeded as exc:
        if time.time() >= row['deadline']:
            raise
        raise ValueError(READ_CLOSED) from exc


def bounded(fn):
    @wraps(fn)
    def invoke(db, token, *args, **kwargs):
        with window(db, token):
            return fn(db, token, *args, **kwargs)
    return invoke
