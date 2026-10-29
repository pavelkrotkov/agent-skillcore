"""Atomically replace verified model history with signed, dependency-bound approvals."""
from contextlib import closing
import sqlite3
import time

from . import compact_seal, compact_targets, compact_capture, compact_dependencies, compact_proofs
from .proof_mode import audit


def preview(root):
    with closing(sqlite3.connect((root / 'curator.sqlite3').as_uri() + '?mode=ro', uri=True)) as db:
        db.row_factory = sqlite3.Row
        db.execute('BEGIN')
        return report(db, compact_targets.targets(db), 'preview')


def report(db, values, state):
    return dict(state=state, publications=sum(p[0] == 'publication' for p in values),
                mappings=sum(p[0] == 'mapping' for p in values),
                transcript_bytes=compact_targets.transcript_bytes(db, values))


def run(db, root, apply=False):
    if not apply:
        return report(db, compact_targets.targets(db), 'preview')
    with db, audit():
        db.execute('BEGIN IMMEDIATE')
        if db.execute("SELECT 1 FROM jobs WHERE state='leased' AND lease_until>? LIMIT 1", (time.time(),)).fetchone():
            raise BlockingIOError('Model workers are active; retry compaction when leases finish')
        compact_seal.initialize(db)
        values = compact_targets.targets(db)
        summary = report(db, values, 'applied')
        stage(db, root, values)
        activate(db, root, values)
    from .audit_reuse import _CACHE
    _CACHE.clear()
    from .compact_artifacts import run as remove_history_copies
    summary['history_copies'] = remove_history_copies(db, root)
    return summary


def stage(db, root, values):
    for identity in values:
        record = compact_capture.capture(db, root, identity)
        compact_seal.write(db, root, identity, record, active=0)
        compact_capture.clear_transient_decoders()
    for identity in values:
        compact_dependencies.verify(db, compact_seal.read(db, root, identity, pending=True))


def activate(db, root, values):
    compact_targets.purge(db, values)
    for identity in values:
        record = compact_seal.read(db, root, identity, pending=True)
        compact_seal.write(db, root, identity, compact_dependencies.activate(db, record), active=1)
    for identity in values:
        compact_proofs.restored(db, root, identity)
