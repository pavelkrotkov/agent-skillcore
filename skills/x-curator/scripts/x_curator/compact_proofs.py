"""Durable approval receipts survive optional cache loss and verifier restarts."""
from marshal import loads

from . import compact_seal, compact_dependencies, compact_validation
from .proof_mode import MaintenanceRequired


def authority(db, root, identity):
    if identity[0] not in compact_seal.KINDS:
        return None
    record = compact_seal.read(db, root, identity)
    if record is None:
        if removed(db, identity):
            raise MaintenanceRequired('Compact approval missing; restore its signed proof, not a retry allowance')
    return record


def restored(db, root, identity):
    record = authority(db, root, identity)
    if record is None:
        return None
    compact_dependencies.verify(db, record)
    value = loads(record['value'])
    getattr(compact_validation, identity[0])(db, root, identity[1], value)
    return value


def removed(db, identity):
    if identity[0] == 'publication':
        row = db.execute('''SELECT e.log FROM publications p JOIN executions e ON e.id=p.proposal
            WHERE p.id=? AND e.finished IS NOT NULL''', (identity[1],)).fetchone()
        return row is not None and row[0] is None
    row = db.execute("SELECT proposal,review FROM wiki_runs WHERE id=? AND state='accepted'", (identity[1],)).fetchone()
    return row is not None and (row[0] is None or row[1] is None)
