"""Explicit recurring permission and one durable request per publication/collection."""
import time
from .receipts import encoded


def initialize(db):
    db.executescript('''
        CREATE TABLE IF NOT EXISTS article_refresh_permissions (
            publication TEXT PRIMARY KEY REFERENCES publications(id),created REAL NOT NULL,reason TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS article_refresh_requests (
            publication TEXT NOT NULL REFERENCES article_refresh_permissions(publication),
            run TEXT NOT NULL REFERENCES intake_runs(run),created REAL NOT NULL,outcome TEXT,
            PRIMARY KEY(publication,run));
    ''')


def enable(db, publication, reason):
    initialize(db)
    from . import article_qualification_store, publication_recovery_store
    article_qualification_store.initialize(db)
    publication_recovery_store.initialize(db)
    if not reason.strip() or len(reason) > 500:
        raise ValueError('concrete recurring article approval required')
    prior = db.execute('''SELECT 1 FROM publication_currentness q JOIN publication_recoveries r
        ON r.publication=q.publication WHERE q.publication=?''', (publication,)).fetchone()
    if prior is None:
        raise ValueError('recurring permission requires a previously qualified and recovered article')
    with db:
        db.execute('INSERT INTO article_refresh_permissions VALUES (?,?,?)', (publication, time.time(), reason))
    return dict(state='checkpoint', publication=publication)


def remaining(db, run):
    return db.execute('''SELECT i.request_limit-c.requests-
        (SELECT count(*) FROM article_refresh_requests a WHERE a.run=i.run)
        FROM intake_runs i JOIN collections c ON c.id=i.run WHERE i.run=?''', (run,)).fetchone()[0]


def reserve(db, publication, current, account):
    run = current['run']
    with db:
        db.execute('BEGIN IMMEDIATE')
        row = db.execute('''SELECT c.account,i.deadline FROM collections c
            JOIN intake_runs i ON i.run=c.id WHERE c.id=?''', (run,)).fetchone()
        if row is None or row['account'] != account or row['deadline'] <= time.time() or remaining(db, run) <= 0:
            raise ValueError('article currentness intake account, deadline or request budget unavailable')
        db.execute('INSERT INTO article_refresh_requests VALUES (?,?,?,NULL)', (publication, run, time.time()))
    return min(row['deadline'], time.time() + 60)


def finish(db, publication, run, outcome):
    with db:
        db.execute('UPDATE article_refresh_requests SET outcome=? WHERE publication=? AND run=?',
                   (encoded(outcome).decode(), publication, run))
