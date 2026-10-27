"""A read-only preview and one atomic, explicitly accepted policy transition."""
from contextlib import closing
import sqlite3
import time

from . import migration_plan, queue, quick_schema, receipts, recovery, retrieval_store
from .storage import open_store

POLICY = migration_plan.POLICY


def initialize(db):
    for module in (queue, receipts, quick_schema, recovery, retrieval_store):
        module.initialize(db)
    db.execute('''CREATE TABLE IF NOT EXISTS policy_transitions (
        policy TEXT NOT NULL, account TEXT NOT NULL, source TEXT NOT NULL,
        created REAL NOT NULL, plan TEXT NOT NULL, prior TEXT NOT NULL,
        PRIMARY KEY(policy,account,source),
        FOREIGN KEY(account,source) REFERENCES jobs(account,id))''')
    db.commit()


def preview(root):
    path = (root / 'curator.sqlite3').resolve()
    with closing(sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)) as source:
        source.row_factory = sqlite3.Row
        source.execute('BEGIN')
        db = sqlite3.connect(':memory:')
        try:
            source.backup(db)
            db.row_factory = sqlite3.Row
            initialize(db)
            return migration_plan.build(db, root, source)
        finally:
            db.close()


def apply(root, expected):
    db = open_store(root)
    try:
        initialize(db)
        with db:
            db.execute('BEGIN IMMEDIATE')
            # ponytail: one offline corpus migration holds the writer lock; split only if this exceeds deployment downtime.
            plan = migration_plan.build(db, root)
            if plan['digest'] != expected or plan['blockers']:
                raise ValueError('migration preview changed or has blockers; review a fresh dry run')
            for item in plan['items']:
                if item['disposition'] == 'quick_check':
                    transition(db, item, expected)
        return dict(plan, applied=True)
    finally:
        db.close()


def transition(db, item, plan):
    job = item['job']
    account, source = item['account'], item['source']
    db.execute('INSERT OR IGNORE INTO jobs(account,id,created) VALUES (?,?,?)', (account, source, item['created']))
    now = time.time()
    db.execute('INSERT INTO policy_transitions VALUES (?,?,?,?,?,?)',
               (POLICY, account, source, now, plan, receipts.encoded(item).decode()))
    before, after = job['max_attempts'], item['grant']['attempt_limit']
    extra = item['grant']['request_extra']
    reason = 'One-time bounded quick-check migration; prior history retained.'
    db.execute('INSERT INTO recovery_grants VALUES (?,?,?,?,?,?,?,?)',
               (item['grant']['id'], account, source, now, reason, before, after, extra))
    db.execute("""UPDATE jobs SET state='pending',max_attempts=?,next_at=0,token=NULL,
        lease_until=NULL,action=? WHERE account=? AND id=?""", (after, reason, account, source))
