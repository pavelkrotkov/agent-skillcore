"""A completed historical approval may finish only its own currently unleased source."""
from .publication_audit import verify_publication
from .read_set import ReadSet
from .publication_recovery_store import recovery


def proof(db, root, identity):
    with db:
        db.execute('BEGIN DEFERRED')
        reads = ReadSet(db)
        row = reads.execute('SELECT * FROM publications WHERE id=?', (identity,)).fetchone()
        if row is None:
            raise ValueError('prepared publication does not exist')
        job = reads.execute('SELECT * FROM jobs WHERE account=? AND id=?', (row['account'], row['source'])).fetchone()
        prior = recovery(reads, identity)
        eligible(row, job, prior)
        owner = reads.execute('''SELECT a.account,a.id,a.token FROM executions e
            JOIN attempts a ON a.token=e.token WHERE e.id=?''', (row['proposal'],)).fetchone()
        if owner is None or tuple(owner)[:2] != (job['account'], job['id']):
            raise ValueError('prepared approval belongs to a different source')
        others = reads.execute("SELECT id FROM publications WHERE account=? AND source=? AND state='published' AND id!=?",
                               (job['account'], job['id'], identity)).fetchall()
        if others:
            raise ValueError('source already has another published version')
        packet, evidence = verify_publication(reads, root, row)
        return dict(row), dict(job), prior, packet, evidence, reads, reads.fingerprint()


def eligible(row, job, prior):
    if job is None or job['token'] is not None or job['lease_until'] is not None:
        raise ValueError('prepared source is still owned by a worker')
    expected = {'invalid': {'retry', 'needs_action', 'awaiting_review'}}
    expected.update({'published': {'published'}} if prior else {'prepared': expected['invalid']})
    if job['state'] not in expected.get(row['state'], ()):
        raise ValueError('only unleased prepared/invalid work or its completed recovery is eligible')
