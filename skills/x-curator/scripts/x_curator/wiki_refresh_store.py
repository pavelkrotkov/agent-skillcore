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
        if count >= attempt_limit(db, refresh) or busy:
            raise ValueError('ZK refresh budget exhausted or organization already running')
        db.execute('INSERT INTO wiki_runs VALUES (?,?,?,?,?,?,NULL,NULL,NULL)',
                   (identity, encoded(inputs).decode(), digest(inputs), now, now + 600, 'running'))
    return identity


def fingerprint(inputs):
    return digest([MODE, sorted(inputs['sources'])])


def selection(publications):
    if not 1 <= len(publications) <= 10 or len(set(publications)) != len(publications):
        raise ValueError('select one to ten distinct retained publications')
    return fingerprint({'sources': dict.fromkeys(publications)})


def attempt_limit(db, refresh):
    return 3 + db.execute('''SELECT (SELECT count(*) FROM wiki_refresh_grants WHERE refresh=?) +
        (SELECT count(*) FROM wiki_refresh_extensions WHERE refresh=?) +
        (SELECT count(*) FROM wiki_refresh_sixth_grants WHERE refresh=?) +
        (SELECT count(*) FROM wiki_refresh_seventh_grants WHERE refresh=?)''', (refresh,) * 4).fetchone()[0]
