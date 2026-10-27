"""Retain interrupted output after the check deadline scopes have unwound."""
import re

from . import provider_health
from .deadlines import DeadlineExceeded
from .native_search_trace import events
from .executions import record_log
from .worker_errors import WorkerFailure


def record(db, state, token, error):
    log = b''
    row = db.execute('''SELECT id,input_sha,log FROM executions
        WHERE token=? AND role IN ('factcheck','factcheck_evidence') AND finished IS NULL ORDER BY started DESC,id DESC LIMIT 1''', (token,)).fetchone()
    if row is not None:
        log = row['log']
        if not log:
            path = state / 'runs' / token / (row['input_sha'] + '.jsonl')
            log = path.read_bytes() if path.exists() else getattr(error, 'log', b'')
        if log:
            record_log(db, row['id'], log)
    failure = provider_failure(error, log)
    if failure:
        provider_health.suspend(db, failure)


def provider_failure(error, log):
    if isinstance(error, WorkerFailure):
        return str(error)
    if isinstance(error, DeadlineExceeded) and transport_exhausted(log):
        return 'subscription stream reconnections exhausted before execution deadline'


def transport_exhausted(log):
    try:
        rows = events(log)
        return not any(row.get('type') == 'turn.completed' for row in rows) and any(
            row.get('type') == 'error' and re.match(
                r'Reconnecting\.\.\. (\d+)/\1 \(stream disconnected before completion:',
                row.get('message', '')) for row in rows)
    except (ValueError, UnicodeError, TypeError, AttributeError):
        return False
