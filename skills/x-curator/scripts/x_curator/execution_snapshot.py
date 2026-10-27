"""Operator-only execution guards retain field evidence without receipt payloads."""
import sqlite3
import sys

from .audit_reuse import snapshot
from .row_fingerprint import row_digest


def field(value):
    length = len(value.encode()) if isinstance(value, str) else len(value) if isinstance(value, bytes) else None
    return dict(type=type(value).__name__, bytes=length, sha256=row_digest(((value,),)).hex())


def capture(db):
    transaction_open = db.in_transaction
    with snapshot(db):
        cursor = db.execute('SELECT rowid,* FROM executions')
        columns = [column[0] for column in cursor.description[1:]]
        revisions = dict(db.execute("SELECT row_id,version FROM proof_rows WHERE table_name='executions'"))
        rows = {str(row[0]): row_record(tuple(row)[1:], columns, revisions.get(row[0])) for row in cursor}
        return dict(format=1, python=sys.version, sqlite=sqlite3.sqlite_version,
                    schema_version=db.execute('PRAGMA schema_version').fetchone()[0],
                    transaction_open=transaction_open, columns=columns, rows=rows)


def row_record(values, columns, revision):
    return dict(sha256=row_digest((values,)).hex(), revision=revision,
                fields={name: field(value) for name, value in zip(columns, values)})


def differences(before, after):
    """Protect baseline rows; new executions are allowed during an authorized cycle."""
    changed = {}
    metadata = [key for key in before.keys() - {'rows'} if before[key] != after.get(key)]
    if metadata:
        changed['metadata'] = sorted(metadata)
    for row_id, prior in before['rows'].items():
        current = after['rows'].get(row_id)
        if prior != current:
            changed[row_id] = row_difference(prior, current)
    return changed


def row_difference(prior, current):
    current = current or dict(fields={}, sha256=None, revision=None)
    columns = prior['fields'].keys() | current['fields'].keys()
    return dict(columns=sorted(name for name in columns if prior['fields'].get(name) != current['fields'].get(name)),
                before=prior, after=current)
