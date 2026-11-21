"""Finite technical retries append child checks without renewing prior allowances."""
import sqlite3
import time

from .deadlines import DeadlineExceeded
from .leases import record_failure
from .worker_errors import WorkerFailure


def technical(error):
    return isinstance(error, (OSError, sqlite3.OperationalError, DeadlineExceeded, WorkerFailure)) or str(error) in (
        'quick-check allowance exhausted', 'fact-check exceeded its durable allowance')


def delay(attempts):
    return min(3600, 60 * 2 ** min(attempts - 1, 6))


def fail(db, token, reason, execution=None):
    with db:
        db.execute('BEGIN IMMEDIATE')
        job = db.execute("SELECT * FROM jobs WHERE token=? AND state='leased'", (token,)).fetchone()
        if job is None:
            return 'superseded'
        check = db.execute('SELECT id,outcome FROM quick_checks WHERE token=?', (token,)).fetchone()
        if check and check['outcome'] is not None:
            raise ValueError('a completed factual disposition cannot be retried as a technical failure')
        now = time.time()
        db.execute("UPDATE quick_checks SET outcome='inconclusive',reason=?,execution=? WHERE token=? AND outcome IS NULL", (reason, execution, token))
        db.execute('INSERT INTO quick_retry_failures VALUES (?,?,?,?)', (token, check['id'] if check else None, now, reason))
        return record_failure(db, dict(job), token, reason, delay(job['attempts']), now)
