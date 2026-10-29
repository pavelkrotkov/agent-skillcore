"""Only finished publication tokens and accepted wiki mappings may lose transcripts."""
from .compact_seal import present


def targets(db):
    sources = [r[0] for r in db.execute('''SELECT p.id FROM publications p JOIN jobs j
        ON j.account=p.account AND j.id=p.source WHERE p.state='published' AND j.state!='leased'
        ORDER BY p.id''')]
    mappings = [r[0] for r in db.execute("SELECT id FROM wiki_runs WHERE state='accepted' ORDER BY id")]
    values = [('publication', p) for p in sources] + [('mapping', p) for p in mappings]
    return [p for p in values if not sealed(db, p)]


def sealed(db, identity):
    return present(db) and db.execute('SELECT 1 FROM compact_approvals WHERE kind=? AND identity=? AND active=1', identity).fetchone() is not None


def token(db, identity):
    return db.execute('''SELECT e.token FROM publications p JOIN executions e ON e.id=p.proposal
        WHERE p.id=?''', (identity,)).fetchone()[0]


def transcript_bytes(db, values):
    tokens = {token(db, p[1]) for p in values if p[0] == 'publication'}
    total = sum(db.execute('SELECT coalesce(sum(length(log)),0) FROM executions WHERE token=? AND finished IS NOT NULL', (t,)).fetchone()[0] for t in tokens)
    for kind, identity in values:
        if kind == 'mapping':
            total += db.execute('SELECT coalesce(length(proposal),0)+coalesce(length(review),0) FROM wiki_runs WHERE id=?', (identity,)).fetchone()[0]
    return total


def purge(db, values):
    tokens = {token(db, p[1]) for p in values if p[0] == 'publication'}
    for t in tokens:
        db.execute('UPDATE executions SET log=NULL WHERE token=? AND finished IS NOT NULL', (t,))
    for kind, identity in values:
        if kind == 'mapping':
            db.execute('UPDATE wiki_runs SET proposal=NULL,review=NULL WHERE id=?', (identity,))
