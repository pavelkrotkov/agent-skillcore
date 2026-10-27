"""Explicit one-time replacement checks for observed fixed retrieval defects."""
import json
import time

from . import native_search, recovery, review_store, retrieval_store
from .receipts import digest
from .quick_recovery_candidates import candidates


def run(db, apply=None):
    review_store.initialize(db)
    recovery.initialize(db)
    retrieval_store.initialize(db)
    with db:
        db.execute('BEGIN IMMEDIATE')
        items = candidates(db)
        identity = digest(['retrieval-repair/v1', native_search.MODE, items])
        if apply is not None and apply != identity:
            raise ValueError('recovery preview changed; inspect a fresh preview')
        if apply is not None:
            for item in items:
                grant(db, item)
    return dict(state='applied' if apply is not None else 'preview', digest=identity, items=items,
                seconds=120, prepared_video_seconds=180, search_mode=native_search.MODE, search_target=3, search_limit=None, extra_requests=20)


def grant(db, item):
    now = time.time()
    db.execute('INSERT INTO quick_recoveries VALUES(?,?,?,?,?,?,NULL)',
               (item['original'], item['replacement'], item['account'], item['source'], now, json.dumps(item['evidence'])))
    limit = max(item['max_attempts'], item['attempts'] + 1)
    db.execute('INSERT INTO recovery_grants VALUES(?,?,?,?,?,?,?,20)',
               (item['replacement'], item['account'], item['source'], now,
                'Bounded replacement for observed retrieval defects', item['max_attempts'], limit))
    db.execute("UPDATE jobs SET state='retry',max_attempts=?,next_at=0,action='Replacement check for repaired retrieval defects' WHERE account=? AND id=?",
               (limit, item['account'], item['source']))
    db.execute("UPDATE curation_batches SET state='open' WHERE id=(SELECT batch FROM curation_members WHERE account=? AND source=?)",
               (item['account'], item['source']))
