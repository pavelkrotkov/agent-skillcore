"""Append-only, source-execution-bound currentness qualifications."""
import json
import time
from contextlib import closing
from . import blobs
from .deadlines import until
from .transport import XClient
from .receipts import digest


def acquire(db, row):
    with until(time.time() + 60), closing(XClient()) as client:
        if client.account != row['account']:
            raise ValueError('article verification account does not match original publication')
        status, body = client.detail(row['source'])
        fetched = time.time()
    return dict(source=row['source'], account=row['account'], status=status, fetched=fetched, body_sha=blobs.put(db, body))


def initialize(db):
    db.execute('''CREATE TABLE IF NOT EXISTS publication_currentness (
        id TEXT PRIMARY KEY, publication TEXT NOT NULL REFERENCES publications(id), receipt TEXT NOT NULL)''')


def retained(db, token):
    if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='publication_currentness'").fetchone() is None:
        return None
    row = db.execute('''SELECT q.* FROM publication_currentness q JOIN publications p ON p.id=q.publication
        JOIN executions e ON e.id=p.proposal WHERE e.token=? ORDER BY q.rowid DESC LIMIT 1''', (token,)).fetchone()
    if row is None:
        return None
    receipt = json.loads(row['receipt'])
    if digest(receipt) != row['id'] or receipt['publication'] != row['publication']:
        raise ValueError('tampered article qualification')
    return receipt
