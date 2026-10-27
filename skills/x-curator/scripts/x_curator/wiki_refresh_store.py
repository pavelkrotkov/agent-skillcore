"""Organization-only attempts have an independent, bounded durable journal."""
from .receipts import digest, encoded
from .wiki_notes import MODE


def reserve(db, inputs, identity, now):
    refresh = inputs['refresh']
    if inputs.get('organization') != MODE or refresh != fingerprint(inputs):
        raise ValueError('invalid ZK refresh identity')
    with db:
        db.execute('BEGIN IMMEDIATE')
        mapped = {row[0] for row in db.execute('SELECT publication FROM wiki_sources WHERE run IS NOT NULL')}
        if not set(inputs['sources']) <= mapped:
            raise ValueError('refresh requires already organized publications')
        count = db.execute("SELECT count(*) FROM wiki_runs WHERE json_extract(input,'$.refresh')=?", (refresh,)).fetchone()[0]
        busy = db.execute("SELECT 1 FROM wiki_runs WHERE state='running' AND expires>?", (now,)).fetchone()
        if count >= 3 or busy:
            raise ValueError('ZK refresh budget exhausted or organization already running')
        db.execute('INSERT INTO wiki_runs VALUES (?,?,?,?,?,?,NULL,NULL,NULL)',
                   (identity, encoded(inputs).decode(), digest(inputs), now, now + 600, 'running'))
    return identity


def fingerprint(inputs):
    return digest([MODE, sorted(inputs['sources'])])
