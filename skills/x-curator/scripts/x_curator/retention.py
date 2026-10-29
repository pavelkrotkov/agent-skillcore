"""Preview or apply bounded retention without touching sources or canonical proofs."""
from . import retention_wiki, retention_memos, retention_history, retention_backups, retention_staging
from .command_lock import lockfile
from contextlib import nullcontext, closing
import sqlite3


def run(db, root, apply=False):
    with lockfile(root, '.wiki.lock') if apply else nullcontext():
        # Validate every namespace before deleting anything from any category.
        for name in ('wiki/builds', 'audit-memos', 'runs', 'policy-transitions'):
            retention_wiki.target(root, name)
        result = dict(state='applied' if apply else 'preview',
                    wiki=retention_wiki.run(db, root, apply),
                    memos=retention_memos.run(db, root, apply),
                    staging=retention_staging.run(db, root, apply),
                    backups=retention_backups.run(root, apply),
                    history=retention_history.run(db, apply))
        from . import compact_history, compact_seal
        if compact_seal.present(db):
            result['proofs'] = compact_history.run(db, root, apply)
        return result


def preview(root):
    path = root / 'curator.sqlite3'
    with closing(sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)) as db:
        db.row_factory = sqlite3.Row
        db.execute('BEGIN')
        return run(db, root)
