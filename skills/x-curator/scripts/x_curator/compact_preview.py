"""Read-only plans for verified approval and superseded diagnostic retention."""
from contextlib import closing
import sqlite3

from . import compact_targets, compact_diagnostics


def preview(root):
    with closing(sqlite3.connect((root / 'curator.sqlite3').as_uri() + '?mode=ro', uri=True)) as db:
        db.row_factory = sqlite3.Row
        db.execute('BEGIN')
        return report(db, compact_targets.targets(db), 'preview')


def report(db, values, state):
    result = dict(state=state, publications=sum(p[0] == 'publication' for p in values),
                mappings=sum(p[0] == 'mapping' for p in values),
                transcript_bytes=compact_targets.transcript_bytes(db, values))
    if state == 'preview':
        result['diagnostics'] = compact_diagnostics.report(db)
    return result


