"""One durable allowance per selected revision, including interrupted quick checks."""
import time

from . import prepared_video
from .leases import require_lease
from .quick_schema import initialize, finish
from .receipts import digest
from .revisions import revision
from .source_evidence import selected_source
from .quick_replacements import latest

POLICY = 'quick-factcheck/v1'


def start(db, token, started):
    initialize(db)
    job = require_lease(db, token, time.time())
    rev = digest(revision(selected_source(db, job)['entry']))
    identity = digest([POLICY, job['account'], job['id'], rev])
    identity = latest(db, job['account'], job['id'], identity)
    seconds = prepared_video.seconds(db, job)
    with db:
        db.execute('BEGIN IMMEDIATE')
        require_lease(db, token, time.time())
        db.execute('INSERT OR IGNORE INTO quick_checks(id,account,source,revision,token,started,deadline) VALUES(?,?,?,?,?,?,?)',
                   (identity, job['account'], job['id'], rev, token, started, min(started + seconds, job['lease_until'] - 2)))
        db.execute('UPDATE quick_checks SET token=? WHERE id=? AND outcome IS NULL', (token, identity))
    return dict(db.execute('SELECT * FROM quick_checks WHERE id=?', (identity,)).fetchone())


def active(db, token):
    require_lease(db, token, time.time())
    row = db.execute('SELECT * FROM quick_checks WHERE token=? AND outcome IS NULL', (token,)).fetchone()
    if row is None:
        from . import deep_store
        if deep_store.exists(db):
            return dict(deep_store.active(db, token), policy=deep_store.POLICY)
    if row is None or time.time() >= row['deadline']:
        raise ValueError('quick-check allowance exhausted')
    return dict(row)


def reserve_search(db, token):
    with db:
        db.execute('BEGIN IMMEDIATE')
        row = active(db, token)
        table, limit = ('deep_runs', 12) if row.get('policy') else ('quick_checks', 3)
        if row['searches'] >= limit:
            raise ValueError('search-query allowance exhausted')
        db.execute(f'UPDATE {table} SET searches=searches+1 WHERE id=?', (row['id'],))
