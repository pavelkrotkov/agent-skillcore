"""Unique recovery receipts preserve completion provenance without altering attempts."""
import json

from .receipts import digest


def initialize(db):
    db.execute('''CREATE TABLE IF NOT EXISTS publication_recoveries (
        publication TEXT PRIMARY KEY REFERENCES publications(id), receipt TEXT NOT NULL, sha TEXT NOT NULL)''')
    db.execute('''CREATE TABLE IF NOT EXISTS publication_reinstatements (
        id TEXT PRIMARY KEY, publication TEXT NOT NULL REFERENCES publications(id), receipt TEXT NOT NULL)''')


def recovery(db, identity):
    table = db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='publication_recoveries'").fetchone()
    row = db.execute('SELECT * FROM publication_recoveries WHERE publication=?', (identity,)).fetchone() if table else None
    if row is None:
        return None
    receipt = json.loads(row['receipt'])
    if digest(receipt) != row['sha'] or receipt['publication'] != identity:
        raise ValueError('tampered publication recovery receipt')
    return receipt
