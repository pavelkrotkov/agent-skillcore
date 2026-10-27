"""Atomically append one authorized replacement allowance per frozen source."""
import json

import repair_manifest as manifest_proof
from repair_eligibility import eligible, job
from x_curator import quick_recovery, recovery
from x_curator.receipts import digest


def prepare(db, manifest, apply=None):
    approval = manifest_proof.identity(manifest)
    if apply not in (None, approval):
        raise ValueError('qualification approval does not match the manifest')
    with db:
        db.execute('BEGIN IMMEDIATE' if apply else 'BEGIN')
        if previously_applied(db, manifest, approval):
            return dict(state='already_applied', digest=approval, scope=manifest['scope'])
        for item in manifest['items']:
            eligible(db, item)
        if apply is not None:
            grant_all(db, manifest, approval)
    return dict(state='applied' if apply else 'preview', digest=approval, scope=manifest['scope'])


def append_grant(db, item, approval):
    candidate = dict(item, replacement=digest(['retrieval-repair/v1', item['original']]), evidence=[])
    quick_recovery.grant(db, candidate)
    evidence = dict(approval=approval, item=item, job_sha=digest(job(db, item)))
    db.execute('UPDATE quick_recoveries SET evidence=? WHERE original=?', (json.dumps(evidence), item['original']))




def previously_applied(db, manifest, approval):
    existing = [manifest_proof.receipt(db, item, approval) for item in manifest['items']]
    if any(existing) and not all(existing):
        raise ValueError('qualification has incomplete recovery receipts')
    return all(existing)


def grant_all(db, manifest, approval):
    recovery.initialize(db)
    for item in manifest['items']:
        append_grant(db, item, approval)
