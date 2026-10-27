"""Expire unreachable memo namespaces after seven days; retain proof evidence."""
import re
from .audit_memo import target as memo_target
from .retention_files import target, old, remove, table


def identities(db):
    values = [('wiki-checkpoint', 0), ('wiki-links', 0)]
    for name, kind in (('publications', 'publication'), ('wiki_runs', 'mapping'), ('wiki_builds', 'wiki-artifacts')):
        if table(db, name):
            values.extend((kind, row[0]) for row in db.execute('SELECT id FROM ' + name))
    return values


def ready(db, root):
    for name, kind, state in (('publications', 'publication', 'published'), ('wiki_runs', 'mapping', 'accepted')):
        if table(db, name):
            for row in db.execute('SELECT id FROM ' + name + ' WHERE state=?', (state,)):
                if not memo_target(root, (kind, row[0]))[0].is_file():
                    return False
    return True


def run(db, root, apply=False):
    folder = target(root, 'audit-memos')
    if not folder.exists():
        return dict(files=0, bytes=0)
    if not ready(db, root):
        return dict(files=0, bytes=0, action='Run wiki --audit --max-sources 0 before pruning historical proof caches')
    keep = {memo_target(root, identity)[0].name for identity in identities(db)}
    paths = [p for p in folder.iterdir() if obsolete(p, keep)]
    return remove(root, paths, apply)


def obsolete(path, keep):
    return bool(re.fullmatch(r'[0-9a-f]{64}\.memo', path.name)) and not path.is_symlink() and path.name not in keep and old(path)
