"""A provider outage cannot consume one research attempt from every queued source."""
import time
import uuid

from .receipts import encoded
from .storage import sha256
from .codex_profile import MODEL

ROUTE = 'chatgpt-' + MODEL


def initialize(db):
    with db:
        db.execute('BEGIN IMMEDIATE')
        db.execute('CREATE TABLE IF NOT EXISTS provider_health (route TEXT PRIMARY KEY,retry_at REAL NOT NULL,action TEXT NOT NULL)')
        columns = {row['name'] for row in db.execute('PRAGMA table_info(provider_health)')}
        for name, kind in (('generation', 'TEXT'), ('failed_at', 'REAL')):
            if name not in columns:
                db.execute('ALTER TABLE provider_health ADD COLUMN ' + name + ' ' + kind)
        db.execute('CREATE TABLE IF NOT EXISTS provider_recoveries (generation TEXT PRIMARY KEY,previous TEXT NOT NULL,started REAL NOT NULL,recovered REAL NOT NULL,log BLOB NOT NULL,log_sha TEXT NOT NULL)')


def current(db):
    initialize(db)
    row = db.execute('SELECT * FROM provider_health WHERE route=?', (ROUTE,)).fetchone()
    return dict(row) if row else None


def blocked(db):
    initialize(db)
    row = db.execute('SELECT retry_at,action FROM provider_health WHERE route=? AND retry_at>?',
                     (ROUTE, time.time())).fetchone()
    return dict(row) if row else None


def suspend(db, action):
    initialize(db)
    now = time.time()
    with db:
        db.execute('INSERT OR REPLACE INTO provider_health(route,retry_at,action,generation,failed_at) VALUES (?,?,?,?,?)',
                   (ROUTE, now + 3600, action, uuid.uuid4().hex, now))


def release(db, failure, started, now, log):
    with db:
        db.execute('BEGIN IMMEDIATE')
        removed = db.execute('DELETE FROM provider_health WHERE route=? AND generation=?',
                             (failure['route'], failure['generation'])).rowcount
        if removed:
            db.execute('INSERT INTO provider_recoveries VALUES (?,?,?,?,?,?)',
                       (failure['generation'], encoded(failure).decode(), started, now, log, sha256(log)))
    return bool(removed)
