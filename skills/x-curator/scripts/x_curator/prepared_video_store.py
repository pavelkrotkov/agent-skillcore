"""Immutable source-revision registry for explicitly approved controller preparations."""
import json
import time
from . import blobs
from .receipts import digest, encoded
from .source_currentness import currentness
from .source_evidence import selected_source
from .prepared_video_urls import urls, capacity
from .video_transcript import qualified


def initialize(db):
    db.execute('''CREATE TABLE IF NOT EXISTS prepared_videos (
        id TEXT PRIMARY KEY,account TEXT NOT NULL,source TEXT NOT NULL,revision TEXT NOT NULL,
        url TEXT NOT NULL,payload TEXT NOT NULL,sha TEXT NOT NULL,reason TEXT NOT NULL,created REAL NOT NULL,
        UNIQUE(account,source,revision,url))''')


def revision(db, job):
    return digest(currentness(selected_source(db, job)['entry']))


def store(db, job, payload, reason):
    from .prepared_video_proof import validate
    initialize(db)
    if not reason.strip() or payload['kind'] != 'video':
        raise ValueError('explicit operator video-preparation approval required')
    selected = selected_source(db, job)['entry']
    if payload['url'] not in urls(selected):
        raise ValueError('prepared video is not selected-post media')
    profile = qualified()
    validate(db, payload, profile)
    current = revision(db, job)
    if json.loads(blobs.read(db, payload['preparation_sha']))['revision'] != current:
        raise ValueError('video package source revision changed during registration')
    capacity(db, job, current, payload)
    identity = digest([job['account'], job['id'], current, payload['url']])
    body = encoded(dict(payload, prepared_video=identity, qualified_profile=profile, quick_scope=True)).decode()
    with db:
        db.execute('INSERT OR IGNORE INTO prepared_videos VALUES (?,?,?,?,?,?,?,?,?)',
                   (identity, job['account'], job['id'], current, payload['url'], body, digest(json.loads(body)), reason, time.time()))
        row = db.execute('SELECT payload FROM prepared_videos WHERE id=?', (identity,)).fetchone()
    if row is None or row[0] != body:
        raise ValueError('preparation already exists; reuse it instead of replacing evidence')
    return identity
