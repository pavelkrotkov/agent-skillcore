"""Validate and spend permission only after a shared worker slot is available."""
import time

from . import deep_permission, deep_store, provider_health, worker_capacity
from .leases import reserve
from .queue import recover
from .review_permissions import require_pending


def claim(db, identity):
    deep_store.initialize(db)
    if provider_health.blocked(db):
        raise ValueError('subscription provider unavailable; approval remains unspent')
    with db:
        db.execute('BEGIN IMMEDIATE')
        now = time.time()
        permission, proposal = deep_permission.verified(db, identity)
        if permission['consumed'] is not None:
            raise ValueError('research approval already consumed')
        recover(db, permission['account'], now)
        require_pending(db, permission['account'], proposal, 'consume')
        if not worker_capacity.available(db, now):
            return None
        seconds = permission['seconds']
        if type(seconds) is not int or not 1 <= seconds <= 14400:
            raise ValueError('explicit research budget must be between 1 and 14400 seconds')
        job = dict(db.execute('SELECT * FROM jobs WHERE account=? AND id=?',
                              (permission['account'], permission['source'])).fetchone())
        job = reserve(db, job, now, seconds + 5)
        db.execute('UPDATE research_permissions SET consumed=? WHERE id=?', (now, identity))
        db.execute('INSERT INTO deep_runs(id,token,started,deadline) VALUES(?,?,?,?)', (identity, job['token'], now, now + seconds))
        return dict(job, approval=identity, deadline=now + seconds, question=permission['question'], scope=permission['scope'])
