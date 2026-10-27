"""Immutable source pages become complete only after exact file readback."""
from .stage_timings import timed
from pathlib import Path
import time

from .leases import require_lease
from .publication_files import write_verified
from .receipts import digest
from .storage import sha256
from .verdicts import approved
from .source_render import render
from .read_set import ReadSet, ChangedDependencies
from .quick_schema import published


@timed("source.publication", scope="selected")
def publish(db, state_root, token, proposal_id, review_id):
    # ponytail: three source-dependency retries; unrelated writers no longer invalidate the proof.
    for attempt in range(3):
        try:
            return publish_once(db, state_root, token, proposal_id, review_id)
        except ChangedDependencies:
            if attempt == 2:
                raise


def publish_once(db, state_root, token, proposal_id, review_id):
    packet, evidence, reads, stamp = proof(db, token, proposal_id, review_id)
    body = render(packet, evidence).encode()
    with db:
        db.execute("BEGIN IMMEDIATE")
        reads.verify(stamp)
        job = require_lease(db, token, time.time())
        identity = digest({"account": job["account"], "source": job["id"], "proposal": proposal_id, "review": review_id})
        path = "wiki/versions/" + identity + ".md"
        db.execute("INSERT OR IGNORE INTO publications VALUES (?,?,?,?,?,?,?,?,?,?)",
                   (identity, job["account"], job["id"], proposal_id, review_id, path, body, sha256(body), "prepared", time.time()))
    write_verified(Path(state_root), path, body)
    _, _, reads, stamp = proof(db, token, proposal_id, review_id)
    with db:
        db.execute("BEGIN IMMEDIATE")
        reads.verify(stamp)
        require_lease(db, token, time.time())
        if (Path(state_root) / path).read_bytes() != body:
            raise ValueError("publication changed before completion")
        published(db, proposal_id)
        db.execute("UPDATE publications SET state='published' WHERE id=?", (identity,))
        db.execute("UPDATE jobs SET state='published',action='verified publication',token=NULL,lease_until=NULL WHERE token=?", (token,))
        db.execute("UPDATE attempts SET state='published',finished=? WHERE token=?", (time.time(), token))
    return identity


@timed("source.proof_replay", scope="selected")
def proof(db, token, proposal, review):
    with db:
        db.execute('BEGIN DEFERRED')
        reads = ReadSet(db)
        packet, evidence = approved(reads, token, proposal, review)
        stamp = reads.fingerprint()
    return packet, evidence, reads, stamp
