"""Mapping attempts and accepted model receipts survive restarts and build failures."""
import json
import time
import uuid

from .receipts import digest, encoded
from . import retrieval_store, wiki_refresh_store


def initialize(db):
    retrieval_store.initialize(db)
    db.executescript('''
        CREATE TABLE IF NOT EXISTS wiki_sources (
            publication TEXT PRIMARY KEY REFERENCES publications(id),attempts INTEGER NOT NULL DEFAULT 0,
            run TEXT,action TEXT NOT NULL DEFAULT 'organize verified claims');
        CREATE TABLE IF NOT EXISTS wiki_runs (
            id TEXT PRIMARY KEY,input TEXT NOT NULL,input_sha TEXT NOT NULL,started REAL NOT NULL,
            expires REAL NOT NULL,state TEXT NOT NULL,proposal BLOB,review BLOB,action TEXT);
        CREATE TABLE IF NOT EXISTS wiki_builds (
            id TEXT PRIMARY KEY,manifest TEXT NOT NULL,created REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS wiki_recovery_grants (
            id TEXT PRIMARY KEY,publication TEXT NOT NULL REFERENCES wiki_sources(publication),
            created REAL NOT NULL,reason TEXT NOT NULL,limit_before INTEGER NOT NULL,limit_after INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS wiki_refresh_grants (
            refresh TEXT PRIMARY KEY,publications TEXT NOT NULL,created REAL NOT NULL,
            reason TEXT NOT NULL,limit_before INTEGER NOT NULL,limit_after INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS wiki_refresh_extensions (
            refresh TEXT PRIMARY KEY REFERENCES wiki_refresh_grants(refresh),publications TEXT NOT NULL,
            created REAL NOT NULL,reason TEXT NOT NULL,
            limit_before INTEGER NOT NULL CHECK(limit_before=4),limit_after INTEGER NOT NULL CHECK(limit_after=5));
        CREATE TABLE IF NOT EXISTS wiki_refresh_sixth_grants (
            refresh TEXT PRIMARY KEY REFERENCES wiki_refresh_extensions(refresh),publications TEXT NOT NULL,
            created REAL NOT NULL,reason TEXT NOT NULL,
            limit_before INTEGER NOT NULL CHECK(limit_before=5),limit_after INTEGER NOT NULL CHECK(limit_after=6));
        CREATE TABLE IF NOT EXISTS wiki_refresh_seventh_grants (
            refresh TEXT PRIMARY KEY REFERENCES wiki_refresh_sixth_grants(refresh),publications TEXT NOT NULL,
            created REAL NOT NULL,reason TEXT NOT NULL,
            limit_before INTEGER NOT NULL CHECK(limit_before=6),limit_after INTEGER NOT NULL CHECK(limit_after=7));
        CREATE TABLE IF NOT EXISTS wiki_refresh_eighth_grants (
            refresh TEXT PRIMARY KEY REFERENCES wiki_refresh_seventh_grants(refresh),publications TEXT NOT NULL,
            created REAL NOT NULL,reason TEXT NOT NULL,
            limit_before INTEGER NOT NULL CHECK(limit_before=7),limit_after INTEGER NOT NULL CHECK(limit_after=8));
    ''')


def attempt_limit(db, source):
    return 3 + db.execute('SELECT count(*) FROM wiki_recovery_grants WHERE publication=?', (source,)).fetchone()[0]


def reserve(db, inputs):
    identity = 'wiki_' + uuid.uuid4().hex
    now = time.time()
    if 'refresh' in inputs:
        return wiki_refresh_store.reserve(db, inputs, identity, now)
    with db:
        db.execute('BEGIN IMMEDIATE')
        for source in inputs['sources']:
            db.execute('INSERT OR IGNORE INTO wiki_sources(publication) VALUES (?)', (source,))
            changed = db.execute('UPDATE wiki_sources SET attempts=attempts+1 WHERE publication=? AND attempts<? AND run IS NULL',
                                 (source, attempt_limit(db, source)))
            if not changed.rowcount:
                raise ValueError('wiki source already mapped or lifetime attempt budget exhausted')
        db.execute("UPDATE wiki_runs SET state='interrupted' WHERE state='running'")
        db.execute('INSERT INTO wiki_runs VALUES (?,?,?,?,?,?,NULL,NULL,NULL)',
                   (identity, encoded(inputs).decode(), digest(inputs), now, now + (600 if inputs.get('organization') else 1800), 'running'))
    return identity


def receipt(db, identity, role, log):
    if role not in ('proposal', 'review'):
        raise ValueError('invalid wiki receipt role')
    with db:
        db.execute('UPDATE wiki_runs SET ' + role + '=? WHERE id=? AND ' + role + ' IS NULL', (log, identity))


def fail(db, identity, action):
    with db:
        db.execute("UPDATE wiki_runs SET state='failed',action=? WHERE id=?", (action, identity))
        inputs = json.loads(db.execute('SELECT input FROM wiki_runs WHERE id=?', (identity,)).fetchone()[0])
        for source in inputs['sources']:
            db.execute('UPDATE wiki_sources SET action=? WHERE publication=? AND run IS NULL', (action, source))
