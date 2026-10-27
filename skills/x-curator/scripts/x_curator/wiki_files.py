"""Immutable generations and an atomic current-generation receipt."""
import os
from pathlib import Path
import uuid

from . import wiki_links
from .publication_files import private_target, write_verified
from .receipts import encoded
from .storage import sha256


def activate(root, identity):
    name = 'wiki/.current-' + uuid.uuid4().hex
    write_verified(root, name, encoded({'generation': identity}))
    target = private_target(root, 'wiki/CURRENT.json')
    os.replace(Path(root) / name, target)
    handle = os.open(target.parent, os.O_RDONLY)
    try:
        os.fsync(handle)
    finally:
        os.close(handle)


def verify_files(root, manifest):
    from .wiki_artifacts import verify
    return verify(root,manifest)


def verify_generation(root, manifest):
    from .wiki_artifacts import verify
    return verify(root,manifest,links=True)


def file_manifest(root, prefix, identity, policy, sources):
    paths = [p for p in (Path(root) / prefix).rglob('*') if p.is_file()]
    if Path(root) / prefix / 'site/index.html' not in paths:
        raise ValueError('rendered wiki index missing from artifact manifest')
    return {'generation': identity, 'policy': policy, 'sources': sorted(sources),
            'files': {str(p.relative_to(root)): sha256(p.read_bytes()) for p in paths}}


def cached(db, root, identity):
    if not (root / 'wiki/builds' / identity / 'site/index.html').is_file():
        return None
    return db.execute('SELECT manifest FROM wiki_builds WHERE id=?', (identity,)).fetchone()
