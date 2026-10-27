"""Read-only verification fences cleanup to one complete current wiki."""
import json
import re
from .storage import sha256
from .retention_files import target, table


def generation(value):
    return isinstance(value, str) and re.fullmatch('[0-9a-f]{64}', value) is not None


def current(db, root):
    pointer = target(root, 'wiki/CURRENT.json')
    if not pointer.exists():
        return None
    identity = json.loads(pointer.read_text())['generation']
    if identity is None:
        return None
    if not generation(identity) or not table(db, 'wiki_builds'):
        raise ValueError('current wiki has no valid generation')
    row = db.execute('SELECT manifest FROM wiki_builds WHERE id=?', (identity,)).fetchone()
    if row is None:
        raise ValueError('current wiki has no build receipt')
    manifest = json.loads(row[0])
    # The caching verifier writes memos; previews must only read original bytes.
    verify(root, identity, manifest)
    return identity


def verify(root, identity, manifest):
    prefix = 'wiki/builds/' + identity + '/'
    if manifest['generation'] != identity or prefix + 'site/index.html' not in manifest['files']:
        raise ValueError('current wiki manifest is incomplete')
    for name, expected in manifest['files'].items():
        if not name.startswith(prefix) or sha256(target(root, name).read_bytes()) != expected:
            raise ValueError('current wiki artifact verification failed')
