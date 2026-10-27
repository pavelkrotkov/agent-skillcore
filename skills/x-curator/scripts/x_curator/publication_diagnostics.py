"""Recheck exactly one publication without restoring it or changing allowances."""
from contextlib import closing
import sqlite3

from .publication_audit import verify_publication


def diagnose(root, identity):
    path = (root / 'curator.sqlite3').resolve()
    with closing(sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)) as db:
        db.row_factory = sqlite3.Row
        db.execute('BEGIN')
        row = db.execute('SELECT * FROM publications WHERE id=?', (identity,)).fetchone()
        if row is None:
            raise ValueError('publication does not exist')
        error = None
        try:
            verify_publication(db, root, row)
        except (ValueError, KeyError, TypeError, OSError) as exc:
            error = type(exc).__name__ + ': ' + str(exc)[:300]
        return dict(publication=identity, state=row['state'], verified=error is None,
                    error=error, failures=history(db, identity))


def history(db, identity):
    if not db.execute("SELECT 1 FROM sqlite_master WHERE name='publication_audit_failures' AND type='table'").fetchone():
        return []
    return [dict(row) for row in db.execute('''SELECT created,error FROM publication_audit_failures
        WHERE publication=? ORDER BY id''', (identity,))]
