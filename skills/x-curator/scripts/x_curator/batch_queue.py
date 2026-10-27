"""Concurrent workers reserve distinct members of the same durable cohort."""
from .stage_timings import timed
import time

from . import batch_store, batch_selection, worker_capacity
from .leases import reserve
from .queue import recover
from .unspent_queue import hold_spent


@timed("queue.select", scope="selected")
def claim(db, account, lease_seconds=240, unspent_only=False):
    if not 1 <= lease_seconds <= 14400:
        raise ValueError('lease must be between 1 and 14400 seconds')
    batch_store.initialize(db)
    with db:
        db.execute('BEGIN IMMEDIATE')
        now = time.time()
        recover(db, account, now)
        if unspent_only:
            hold_spent(db, account)
        if not worker_capacity.available(db, now):
            return None
        db.execute('INSERT OR IGNORE INTO queue_turns(account) VALUES (?)', (account,))
        identity = batch_selection.current(db, account, now, unspent_only)
        row = db.execute("""SELECT j.* FROM jobs j JOIN curation_members m ON m.account=j.account AND m.source=j.id
            WHERE m.batch=? AND j.state IN ('pending','retry') AND j.next_at<=? AND j.attempts<j.max_attempts AND (?=0 OR j.attempts=0)
            ORDER BY j.created,j.id LIMIT 1""", (identity, now, unspent_only)).fetchone()
        if row is None:
            return None
        job = reserve(db, dict(row), now, lease_seconds)
        db.execute('UPDATE daily_settings SET turn=turn+1 WHERE account=?', (account,))
        return dict(job, batch=identity)
