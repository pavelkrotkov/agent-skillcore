"""Seal closed-attempt diagnostics without granting them publication authority."""
import json

from . import compact_diagnostic_targets as targets, compact_provenance, compact_output, compact_seal, compact_diagnostic_bindings
from .receipts import digest
from .storage import sha256


def intact(row):
    try:
        return (sha256(row['log']) == row['log_sha'] and
                digest(json.loads(row['input'])) == row['input_sha'] and
                digest(json.loads(row['output'])) == row['output_sha'])
    except (ValueError, TypeError):
        return False


def eligible(db):
    for attempt in targets.candidates(db):
        rows = targets.rows(db, attempt['token'])
        if all(intact(row) for row in rows):
            yield attempt, rows


def report(db):
    count, size = 0, 0
    for attempt, rows in eligible(db):
        count += 1
        size += sum(len(row['log']) for row in rows) + compact_output.savings(db, attempt['token'])
    return dict(attempts=count, transcript_bytes=size)


def run(db, root):
    result = dict(attempts=0, transcript_bytes=0)
    if not targets.candidates(db):
        return result
    compact_diagnostic_bindings.verify(db, root)
    for attempt, rows in eligible(db):
        targets.require_approval(db, root, attempt)
        result['attempts'] += 1
        result['transcript_bytes'] += sum(len(row['log']) for row in rows) + compact_output.savings(db, attempt['token'])
        provenance = compact_provenance.attempt(db, attempt['token'])
        record = dict(version=1, type='superseded-diagnostic/v1', attempt=dict(attempt), provenance=provenance)
        compact_seal.write(db, root, ('diagnostic', attempt['token']), record, active=1)
        db.executemany('UPDATE executions SET log=NULL WHERE id=?', [(row['id'],) for row in rows])
        compact_output.purge(db, attempt['token'])
    if result['attempts']:
        compact_diagnostic_bindings.refresh(db, root)
    return result
