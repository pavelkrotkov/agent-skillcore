"""Verify accepted source receipts without erasing their history.

Missing historical checkpoints require maintenance, never invalidation or retries.
Only an actual source-verification failure may withdraw a publication.
"""
from .stage_timings import timed
import time
import os
from pathlib import Path

from .evidence import current_bundle
from .publication_files import write_verified
from .source_render import render
from .storage import sha256
from .verdicts import validate_approval
from .audit_reuse import cached
from .read_set import read_file
from .wiki_admission import historical_sources


@timed("source.full_audit", scope="corpus")
def audit(db, root):
    previous=historical_sources(db)
    invalid = []
    for row in db.execute("SELECT * FROM publications WHERE state='published'").fetchall():
        try:
            verify_publication(db, root, row,required=row['id'] in previous)
        except (ValueError, KeyError, TypeError, OSError) as exc:
            invalidate(db, row, type(exc).__name__ + ': ' + str(exc)[:300])
            invalid.append(row["id"])
    return invalid


def verify_publication(db, root, row, required=False):
    return cached(db, root, ('publication', row['id']), lambda reads: verify_source(reads, root, row['id']),required=required)


def verify_source(db, root, identity):
    row = db.execute('SELECT * FROM publications WHERE id=?', (identity,)).fetchone()
    token = db.execute("SELECT token FROM executions WHERE id=?", (row["proposal"],)).fetchone()[0]
    job = db.execute("SELECT * FROM jobs WHERE account=? AND id=?", (row["account"], row["source"])).fetchone()
    evidence = current_bundle(db, job, token)
    packet, _ = validate_approval(db, token, row["proposal"], row["review"], evidence)
    expected = render(packet, evidence).encode()
    if row["body"] != expected or row["sha"] != sha256(expected) or read_file(db, root, row['path']) != expected:
        raise ValueError("publication differs from verified evidence")
    return packet, evidence


def invalidate(db, row, error):
    error = f'pid={os.getpid()} code={Path(__file__).resolve().parents[4].name[:20]}; {error}'[:300]
    action = ('source revision changed; recapture and re-review' if 'source revision changed' in error
              else 'publication readback failed; restore and reverify')
    with db:
        db.execute('INSERT INTO publication_audit_failures(publication,created,error) VALUES (?,?,?)',
                   (row['id'], time.time(), error))
        db.execute("UPDATE publications SET state='invalid' WHERE id=?", (row["id"],))
        db.execute("""UPDATE jobs SET state=CASE WHEN attempts<max_attempts THEN 'retry' ELSE 'needs_action' END,
            next_at=?,action=? WHERE account=? AND id=? AND state='published'""",
                   (time.time(), action, row["account"], row["source"]))


def replay_file(db, root, identity):
    row = db.execute("SELECT * FROM publications WHERE id=?", (identity,)).fetchone()
    if row is None or sha256(row["body"]) != row["sha"]:
        raise ValueError("missing or tampered publication receipt")
    write_verified(root, row["path"], row["body"])
    # Restoring bytes alone cannot reinstate completion; a fresh lease/review must do that.
    return row["path"]


def inventory(db, root, account, source, proof_db=None):
    result = []
    for row in db.execute("SELECT * FROM publications WHERE account=? AND source=? AND state='published' ORDER BY id", (account, source)):
        error = None
        try:
            verify_publication(proof_db or db, root, row)
        except (ValueError, KeyError, TypeError, OSError) as exc:
            error = type(exc).__name__ + ': ' + str(exc)[:300]
        result.append(dict(id=row['id'], sha=row['sha'], error=error))
    return result
