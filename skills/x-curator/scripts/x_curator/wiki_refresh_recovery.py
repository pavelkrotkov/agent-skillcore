"""A selection may receive one explicit grant without resetting any earlier run."""
import time

from .receipts import encoded
from .wiki_refresh_store import selection, attempt_limit
from .wiki_store import initialize


def exhausted(db, publications, refresh):
    mapped = {row[0] for row in db.execute('''SELECT s.publication FROM wiki_sources s
        JOIN publications p ON p.id=s.publication JOIN jobs j ON j.account=p.account AND j.id=p.source
        WHERE s.run IS NOT NULL AND p.state='published' AND j.state='published' ''')}
    count = db.execute("SELECT count(*) FROM wiki_runs WHERE json_extract(input,'$.refresh')=?", (refresh,)).fetchone()[0]
    return set(publications) <= mapped and count == 3 and attempt_limit(db, refresh) == 3


def grant(db, publications, reason):
    refresh = selection(publications)
    if not reason.strip() or len(reason) > 500:
        raise ValueError('concrete refresh recovery reason required')
    initialize(db)
    with db:
        db.execute('BEGIN IMMEDIATE')
        if db.execute("SELECT 1 FROM wiki_runs WHERE state='running' AND expires>?", (time.time(),)).fetchone():
            raise ValueError('refresh recovery cannot overlap an active mapping run')
        if not exhausted(db, publications, refresh):
            raise ValueError('only exhausted retained selections qualify for one lifetime refresh grant')
        db.execute('INSERT INTO wiki_refresh_grants VALUES (?,?,?,?,?,?)',
                   (refresh, encoded(sorted(publications)).decode(), time.time(), reason, 3, 4))
    return dict(state='checkpoint', refresh=refresh, attempt_limit=4)
