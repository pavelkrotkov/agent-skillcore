"""Approved runs have separate durable allowances; quick checks remain immutable."""
import time

from . import review_store
from .leases import require_lease

POLICY = 'approved-research/v1'


def initialize(db):
    review_store.initialize(db)
    db.executescript('''CREATE TABLE IF NOT EXISTS deep_runs (
        id TEXT PRIMARY KEY REFERENCES research_permissions(id), token TEXT UNIQUE NOT NULL,
        started REAL NOT NULL, deadline REAL NOT NULL, searches INTEGER NOT NULL DEFAULT 0,
        outcome TEXT, reason TEXT, execution TEXT, review_batch TEXT REFERENCES curation_batches(id));''')


def active(db, token):
    require_lease(db, token, time.time())
    row = db.execute('SELECT * FROM deep_runs WHERE token=? AND outcome IS NULL', (token,)).fetchone()
    if row is None or time.time() >= row['deadline']:
        raise ValueError('approved research allowance exhausted')
    return dict(row)


def exists(db):
    return db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='deep_runs'").fetchone() is not None


def finish(db, token, outcome, reason, execution=None):
    with db:
        db.execute('BEGIN IMMEDIATE')
        require_lease(db, token, time.time())
        db.execute('UPDATE deep_runs SET outcome=?,reason=?,execution=? WHERE token=?', (outcome, reason, execution, token))
        state = 'excluded' if outcome == 'disproven' else 'awaiting_review'
        db.execute('UPDATE jobs SET state=?,action=?,token=NULL,lease_until=NULL WHERE token=?', (state, reason, token))
        db.execute('UPDATE attempts SET state=?,action=?,finished=? WHERE token=?', (state, reason, time.time(), token))


def recover(db, account, now):
    if not exists(db):
        return
    rows = db.execute('''SELECT j.token FROM jobs j JOIN deep_runs d ON d.token=j.token
        WHERE j.account=? AND j.state='leased' AND j.lease_until<=?''', (account, now)).fetchall()
    for row in rows:
        token = row['token']
        reason = 'Approved research interrupted; its original permission remains spent.'
        db.execute("UPDATE deep_runs SET outcome=COALESCE(outcome,'inconclusive'),reason=COALESCE(reason,?) WHERE token=?", (reason, token))
        db.execute("UPDATE attempts SET state='interrupted',finished=?,action=? WHERE token=?", (now, reason, token))
        db.execute("UPDATE jobs SET state='awaiting_review',action=?,token=NULL,lease_until=NULL WHERE token=?", (reason, token))
