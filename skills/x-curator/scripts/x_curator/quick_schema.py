"""Durable quick-check allowances and exact dynamic-tool records."""

import json
import time
from .leases import require_lease
from .quick_replacements import migrate


def initialize(db):
    db.executescript('''CREATE TABLE IF NOT EXISTS quick_checks (
        id TEXT PRIMARY KEY, account TEXT NOT NULL, source TEXT NOT NULL, revision TEXT NOT NULL,
        token TEXT NOT NULL, started REAL NOT NULL, deadline REAL NOT NULL,
        searches INTEGER NOT NULL DEFAULT 0, outcome TEXT, reason TEXT, execution TEXT);
        CREATE TABLE IF NOT EXISTS quick_tools (
        id TEXT PRIMARY KEY, token TEXT NOT NULL, name TEXT NOT NULL, arguments TEXT NOT NULL,
        output TEXT, created REAL NOT NULL, finished REAL);
        CREATE INDEX IF NOT EXISTS quick_tools_token ON quick_tools(token);
        CREATE TABLE IF NOT EXISTS quick_sources (
        token TEXT NOT NULL, id TEXT NOT NULL, url TEXT NOT NULL, PRIMARY KEY(token,id));
        CREATE TABLE IF NOT EXISTS quick_recoveries (
        original TEXT PRIMARY KEY REFERENCES quick_checks(id), replacement TEXT UNIQUE NOT NULL,
        account TEXT NOT NULL, source TEXT NOT NULL, created REAL NOT NULL, evidence TEXT NOT NULL,
        review_batch TEXT);''')
    migrate(db)



def finish(db, token, outcome, reason, execution=None):
    with db:
        db.execute('BEGIN IMMEDIATE')
        require_lease(db, token, time.time())
        db.execute('UPDATE quick_checks SET outcome=?,reason=?,execution=? WHERE token=?',
                   (outcome, reason, execution, token))
        if outcome != 'supported':
            state = 'excluded' if outcome == 'disproven' else 'awaiting_review'
            db.execute('UPDATE jobs SET state=?,action=?,token=NULL,lease_until=NULL WHERE token=?', (state, reason, token))
            db.execute('UPDATE attempts SET state=?,action=?,finished=? WHERE token=?', (state, reason, time.time(), token))


def published(db, execution):
    row = db.execute('SELECT role,output,token,input FROM executions WHERE id=?', (execution,)).fetchone()
    if row['role'] == 'factcheck':
        from .quick_final import output
        decision = output(db, execution)
        table = 'deep_runs' if json.loads(row['input']).get('policy') == 'approved-research/v1' else 'quick_checks'
        db.execute(f"UPDATE {table} SET outcome='supported',reason=?,execution=? WHERE token=?",
                   (decision['reason'], execution, row['token']))
