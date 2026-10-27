"""Explicit fourth and fifth grants append records without resetting earlier runs."""
import time

from .receipts import encoded
from .wiki_refresh_store import selection, attempt_limit
from .wiki_store import initialize


def exhausted(db, publications, refresh, limit):
    mapped = {row[0] for row in db.execute('''SELECT s.publication FROM wiki_sources s
        JOIN publications p ON p.id=s.publication JOIN jobs j ON j.account=p.account AND j.id=p.source
        WHERE s.run IS NOT NULL AND p.state='published' AND j.state='published' ''')}
    count = db.execute("SELECT count(*) FROM wiki_runs WHERE json_extract(input,'$.refresh')=?", (refresh,)).fetchone()[0]
    return set(publications) <= mapped and count == limit and attempt_limit(db, refresh) == limit


def grant(db, publications, reason, *, fifth=False):
    refresh = selection(publications)
    if not reason.strip() or len(reason) > 500:
        raise ValueError('concrete refresh recovery reason required')
    initialize(db)
    limit = 4 if fifth else 3
    table = 'wiki_refresh_extensions' if fifth else 'wiki_refresh_grants'
    with db:
        db.execute('BEGIN IMMEDIATE')
        if db.execute("SELECT 1 FROM wiki_runs WHERE state='running' AND expires>?", (time.time(),)).fetchone():
            raise ValueError('refresh recovery cannot overlap an active mapping run')
        if not exhausted(db, publications, refresh, limit):
            raise ValueError('only exhausted retained selections at the requested limit qualify for a refresh grant')
        db.execute(f'INSERT INTO {table} VALUES (?,?,?,?,?,?)',
                   (refresh, encoded(sorted(publications)).decode(), time.time(), reason, limit, limit + 1))
    return dict(state='checkpoint', refresh=refresh, attempt_limit=limit + 1)
