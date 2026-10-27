"""Explicitly recover one verified page without changing research allowances."""
from .stage_timings import timed
import time

from .prepared_proof import proof
from .quick_schema import published
from .publication_recovery_store import initialize
from .publication_files import private_target
from .receipts import digest, encoded


@timed("source.recovery", scope="selected")
def complete(db, root, identity, reason):
    if not reason.strip() or len(reason) > 500:
        raise ValueError('concrete publication recovery reason required')
    initialize(db)
    row, job, previous, packet, evidence, reads, stamp = proof(db, root, identity)
    receipt = dict(publication=identity, reason=reason, prior_job=job, prior_publication_state=row['state'], proposal=row['proposal'], review=row['review'],
                   packet_sha=digest(packet), bundle_sha=digest(evidence), body_sha=row['sha'], completed=time.time())
    with db:
        db.execute('BEGIN IMMEDIATE')
        reads.verify(stamp)
        if private_target(root, row['path']).read_bytes() != row['body']:
            raise ValueError('prepared page changed before completion')
        if previous and row['state'] == 'published':
            return dict(state='published', publication=identity, already_completed=True)
        record(db, row, previous, receipt)
        db.execute("UPDATE publications SET state='published' WHERE id=?", (identity,))
        db.execute("UPDATE jobs SET state='published',action='completed verified prepared publication' WHERE account=? AND id=?",
                   (job['account'], job['id']))
    return dict(state='published', publication=identity, already_completed=False)


def record(db, row, previous, receipt):
    body, sha = encoded(receipt).decode(), digest(receipt)
    if not previous:
        db.execute('INSERT INTO publication_recoveries VALUES (?,?,?)', (row['id'], body, sha))
    if row['state'] == 'invalid':
        db.execute('INSERT INTO publication_reinstatements VALUES (?,?,?)', (sha, row['id'], body))
    else:
        published(db, row['proposal'])
