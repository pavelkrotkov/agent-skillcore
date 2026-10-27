"""Stable private cohorts reuse the existing account/source identity and leases."""
import uuid

from . import quick_schema, receipts, daily_store
from .queue import enqueue


def initialize(db):
    enqueue(db)
    receipts.initialize(db)
    quick_schema.initialize(db)
    db.executescript('''CREATE TABLE IF NOT EXISTS curation_batches (
        id TEXT PRIMARY KEY, account TEXT NOT NULL, kind TEXT NOT NULL, created REAL NOT NULL,
        cutoff REAL NOT NULL, state TEXT NOT NULL DEFAULT 'open');
        CREATE TABLE IF NOT EXISTS curation_members (
        batch TEXT NOT NULL REFERENCES curation_batches(id), account TEXT NOT NULL, source TEXT NOT NULL,
        PRIMARY KEY(account,source), FOREIGN KEY(account,source) REFERENCES jobs(account,id));''')
    daily_store.initialize(db)


def close_finished(db, account):
    db.execute("""UPDATE curation_batches SET state=CASE WHEN EXISTS (
        SELECT 1 FROM curation_members m JOIN jobs j ON j.account=m.account AND j.id=m.source
        WHERE m.batch=curation_batches.id AND j.state IN ('pending','retry','leased'))
        THEN 'open' ELSE 'closed' END WHERE account=?""", (account,))


def form(db, account, now):
    rows = db.execute("""SELECT j.id FROM jobs j WHERE j.account=? AND j.state!='published'
        AND NOT EXISTS (SELECT 1 FROM daily_settings d WHERE d.account=j.account AND j.created>=d.baseline)
        AND NOT EXISTS (SELECT 1 FROM curation_members m WHERE m.account=j.account AND m.source=j.id)
        ORDER BY j.created,j.id LIMIT 50""", (account,)).fetchall()
    if not rows:
        return None
    identity = uuid.uuid4().hex
    db.execute("INSERT INTO curation_batches(id,account,kind,created,cutoff) VALUES (?,?,'backlog',?,?)", (identity, account, now, now))
    db.executemany('INSERT INTO curation_members VALUES (?,?,?)', [(identity, account, row['id']) for row in rows])
    return identity
