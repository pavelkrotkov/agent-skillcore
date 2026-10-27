"""Bound recognized migration snapshots; unknown operator files are untouched."""
from .retention_files import target, old, remove


def run(root, apply=False):
    paths = list(root.glob('*-before.sqlite3'))
    folder = target(root, 'policy-transitions')
    if folder.exists():
        paths.extend(folder.glob('*/before.sqlite3'))
        paths.extend(folder.glob('*/before-migration.sqlite3'))
    paths = [target(root, str(p.relative_to(root))) for p in paths]
    paths.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    expired = [p for p in paths[2:] if old(p, 30) and idle(p)]
    return remove(root, expired, apply)


def idle(path):
    for suffix in ('-wal', '-journal'):
        pending = path.with_name(path.name + suffix)
        if pending.exists() and (pending.is_symlink() or pending.stat().st_size):
            return False
    return True
