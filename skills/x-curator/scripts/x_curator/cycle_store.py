"""Persist cycle bounds and phases before work; labels alone never prove liveness."""
import os
import time
import uuid

from .process_liveness import start_mark
from .receipts import encoded
from .retention_history import summary


def initialize(db):
    db.execute('''CREATE TABLE IF NOT EXISTS cycles (
        id TEXT PRIMARY KEY,started REAL NOT NULL,deadline REAL NOT NULL,finished REAL,
        pid INTEGER NOT NULL,process_start TEXT,stage TEXT NOT NULL,state TEXT NOT NULL,result TEXT)''')


def begin(db, seconds):
    initialize(db)
    identity = uuid.uuid4().hex
    now = time.time()
    with db:
        db.execute('INSERT INTO cycles VALUES (?,?,?,NULL,?,?,?,?,NULL)',
                   (identity, now, now + seconds, os.getpid(), start_mark(os.getpid()), 'starting', 'running'))
    return identity, now + seconds


def stage(db, identity, name):
    with db:
        db.execute('UPDATE cycles SET stage=? WHERE id=?', (name, identity))


def finish(db, identity, state, result):
    with db:
        db.execute('UPDATE cycles SET finished=?,state=?,result=? WHERE id=?',
                   (time.time(), state, encoded(summary(result)).decode(), identity))
