"""Explicit recovery of retained controller failures; factual decisions stay terminal."""
import time

from . import review_store
from .receipts import digest

from .quick_retry_candidates import candidates


def run(db, account, apply=None, sources=()):
    review_store.initialize(db)
    with db:
        if apply is not None:
            db.execute('BEGIN IMMEDIATE')
        items = candidates(db, account, sources)
        identity = digest(['technical-recovery/v1', account, sorted(sources), items])
        if apply is not None:
            apply_items(db, identity, apply, items)
    return dict(state='applied' if apply is not None else 'preview', digest=identity, items=items,
                extra_attempts=0, extra_requests=0)


def apply_items(db, identity, approval, items):
    if approval != identity:
        raise ValueError('technical recovery preview changed; inspect a fresh preview')
    for item in items:
        requeue(db, item)


def requeue(db, item):
    db.execute('INSERT INTO quick_retry_failures VALUES (?,?,?,?)',
               (item['token'], item['check'], time.time(), item['reason']))
    db.execute("UPDATE jobs SET state='retry',next_at=?,action='bounded technical retry scheduled' WHERE account=? AND id=?",
               (item['next_at'], item['account'], item['source']))
