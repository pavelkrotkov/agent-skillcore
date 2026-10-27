"""Claim only authorized manifest members; an interrupted claim is spent."""
import time

import repair_manifest as manifest_proof
from repair_eligibility import job, unchanged
from repair_qualification import prepare
from repair_report import outcomes
from x_curator import leases, provider_health, wiki, worker_capacity, worker_process
from x_curator.receipts import digest


def claim(db, item, approval):
    with db:
        db.execute('BEGIN IMMEDIATE')
        evidence = manifest_proof.receipt(db, item, approval)
        if evidence is None:
            raise ValueError('qualification requires its exact recovery receipt')
        current = job(db, item)
        if current['attempts'] > item['attempts']:
            return None
        unchanged(db, item)
        if digest(current) != evidence['job_sha'] or current['state'] != 'retry':
            raise ValueError('qualification job changed after its grant')
        if not worker_capacity.available(db, time.time()):
            raise ValueError('qualification waits for a free source-worker slot')
        db.execute('INSERT OR IGNORE INTO queue_turns(account) VALUES (?)', (item['account'],))
        return leases.reserve(db, current, time.time(), 180)


def run(db, root, client, manifest, approval):
    if any(item['account'] != client.account for item in manifest['items']):
        raise ValueError('qualification account differs from the authenticated session')
    prepare(db, manifest, approval)
    for item in manifest['items']:
        dependency = provider_health.blocked(db)
        if dependency:
            break
        current = claim(db, item, approval)
        if current:
            worker_process.process(db, root, client, current)
    return dict(state='blocked' if dependency else 'checkpoint', dependency=dependency,
                digest=approval, results=outcomes(db, manifest), wiki=wiki.run(db, root, 0))
