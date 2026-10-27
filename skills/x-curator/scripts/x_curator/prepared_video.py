"""Attach only unchanged, source-bound prepared video evidence to quick checks."""
import json
import time
from .evidence import save_capture
from .receipts import digest
from .prepared_video_store import revision, store
from .leases import require_lease


def attach(db, token):
    job = require_lease(db, token, time.time())
    for row in registered(db, job):
        save_capture(db, token, json.loads(row[0]))


def exists(db):
    return db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='prepared_videos'").fetchone()


def verify(db, captures, job):
    for payload in captures.values():
        if 'prepared_video' in payload:
            verify_one(db, payload, job)


def verify_one(db, payload, job):
    from .prepared_video_proof import validate
    row = db.execute('SELECT * FROM prepared_videos WHERE id=?', (payload['prepared_video'],)).fetchone() if exists(db) else None
    if row is None:
        raise ValueError('foreign prepared video')
    if (row['account'], row['source'], row['revision'], row['sha']) != (
            job['account'], job['id'], revision(db, job), digest(payload)) or json.loads(row['payload']) != payload:
        raise ValueError('stale, foreign or tampered prepared video')
    from . import blobs
    manifest = json.loads(blobs.read(db, payload['preparation_sha']))
    if manifest['revision'] != row['revision']:
        raise ValueError('prepared video manifest revision differs from registry')
    validate(db, payload, payload['qualified_profile'])


def registered(db, job):
    if not exists(db):
        return []
    return db.execute('SELECT payload FROM prepared_videos WHERE account=? AND source=? AND revision=?',
                      (job['account'], job['id'], revision(db, job))).fetchall()


def seconds(db, job):
    rows = registered(db, job)
    for row in rows:
        verify_one(db, json.loads(row['payload']), job)
    return 180 if rows else 120
