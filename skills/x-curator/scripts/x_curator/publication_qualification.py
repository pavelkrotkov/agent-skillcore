"""Explicit model-free article qualification preserves original publication proof."""
import json
from .receipts import digest, encoded
from .source_evidence import selected_source
from .publication_currentness import selection, verify
from .article_qualification_store import initialize, acquire
from .prepared_proof import eligible
from .publication_recovery_store import recovery


def qualify(db, publication, reason):
    initialize(db)
    row = db.execute('SELECT p.*,e.token FROM publications p JOIN executions e ON e.id=p.proposal WHERE p.id=?', (publication,)).fetchone()
    if row is None or row['state'] != 'invalid':
        raise ValueError('article qualification requires an existing withdrawn publication')
    job = db.execute('SELECT * FROM jobs WHERE account=? AND id=?', (row['account'], row['source'])).fetchone()
    eligible(row, job, recovery(db, publication))
    current = selected_source(db, job)
    receipt = dict(acquire(db, row), publication=publication, reason=reason, selection=selection(current))
    captures = {c['id']: json.loads(c['payload']) for c in db.execute('SELECT * FROM captures WHERE token=?', (row['token'],))}
    with db:
        db.execute('INSERT INTO publication_currentness VALUES (?,?,?)', (digest(receipt), publication, encoded(receipt).decode()))
    verify(db, receipt, captures, selected_source(db, job))
