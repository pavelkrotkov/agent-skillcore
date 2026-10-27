"""Explicit, finite mapping allowances preserve failed attempts and native receipts."""
from .stage_timings import timed
import time
import uuid

from .wiki_store import initialize, attempt_limit


@timed("wiki.mapping_recovery", scope="selected")
def grant(db, publication, reason):
    if not reason.strip() or len(reason) > 500:
        raise ValueError('concrete mapping recovery reason required')
    initialize(db)
    with db:
        db.execute('BEGIN IMMEDIATE')
        if db.execute("SELECT 1 FROM wiki_runs WHERE state='running' AND expires>?", (time.time(),)).fetchone():
            raise ValueError('mapping recovery cannot overlap an active mapping run')
        row = db.execute('''SELECT s.* FROM wiki_sources s JOIN publications p ON p.id=s.publication
            JOIN jobs j ON j.account=p.account AND j.id=p.source
            WHERE s.publication=? AND p.state='published' AND j.state='published' AND s.run IS NULL''', (publication,)).fetchone()
        limit = attempt_limit(db, publication)
        if row is None or row['attempts'] != limit or limit >= 5:
            raise ValueError('only exhausted unmapped publications qualify; at most two lifetime mapping grants')
        identity = uuid.uuid4().hex
        db.execute('INSERT INTO wiki_recovery_grants VALUES (?,?,?,?,?,?)',
                   (identity, publication, time.time(), reason, limit, limit + 1))
    return {'state': 'checkpoint', 'grant': identity, 'publication': publication, 'attempt_limit': limit + 1}
