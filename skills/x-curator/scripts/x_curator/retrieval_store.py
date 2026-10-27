"""Durable request reservations share the private corpus database."""
from contextlib import contextmanager
import time
import uuid

from . import blobs
from .deadlines import until
from .leases import require_lease
from .recovery import request_limit


def initialize(db):
    db.execute("""CREATE TABLE IF NOT EXISTS retrievals (
        id TEXT PRIMARY KEY,token TEXT NOT NULL REFERENCES attempts(token),
        account TEXT NOT NULL,source TEXT NOT NULL,url TEXT NOT NULL,
        started REAL NOT NULL,finished REAL,status INTEGER,body_sha TEXT,error TEXT,
        FOREIGN KEY(account,source) REFERENCES jobs(account,id))""")
    db.execute('CREATE INDEX IF NOT EXISTS retrievals_source_finished ON retrievals(account,source,finished)')


def reserve(db, token, url):
    initialize(db)
    identity = uuid.uuid4().hex
    with db:
        db.execute("BEGIN IMMEDIATE")
        job = require_lease(db, token, time.time())
        used = db.execute("SELECT count(*) FROM retrievals WHERE account=? AND source=?", (job["account"], job["id"])).fetchone()[0]
        if used >= request_limit(db, job['account'], job['id']):
            raise ValueError("source lifetime acquisition budget exhausted")
        db.execute("INSERT INTO retrievals(id,token,account,source,url,started) VALUES (?,?,?,?,?,?)",
                   (identity, token, job["account"], job["id"], url, time.time()))
    return identity


def finish(db, identity, status, body):
    body_sha = blobs.put(db, body)
    with db:
        db.execute("UPDATE retrievals SET finished=?,status=?,body_sha=? WHERE id=?", (time.time(), status, body_sha, identity))
    return body_sha


@contextmanager
def reserved(db, token, url):
    identity = reserve(db, token, url)
    try:
        with until(time.time() + 60):
            yield identity
    except Exception as exc:
        with db:
            db.execute("UPDATE retrievals SET finished=?,error=? WHERE id=?", (time.time(), type(exc).__name__, identity))
        raise
