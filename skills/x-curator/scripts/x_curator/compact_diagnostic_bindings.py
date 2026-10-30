"""Rebind only controlled transcript removal after authenticating every prior dependency."""
from marshal import dumps

from . import compact_seal, compact_dependencies, compact_proofs
from .audit_seal import policy
from .storage import sha256


def identities(db):
    return [tuple(row) for row in db.execute("SELECT kind,identity FROM compact_approvals WHERE active=1 AND kind!='diagnostic'")]


def verify(db, root):
    for identity in identities(db):
        compact_dependencies.verify(db, compact_seal.read(db, root, identity))


def refresh(db, root):
    for identity in identities(db):
        prior = compact_seal.read(db, root, identity)
        updated = compact_dependencies.activate(db, prior)
        if updated['queries'] != prior['queries']:
            provenance = dict(prior['provenance'])
            migrations = provenance.get('transcript_rebindings', [])
            provenance['transcript_rebindings'] = migrations + [dict(prior_queries_sha=sha256(dumps(prior['queries'])), verifier=policy(identity[0]))]
            updated['provenance'] = provenance
            compact_seal.write(db, root, identity, updated, active=1)
            compact_proofs.restored(db, root, identity)
    verify(db, root)
