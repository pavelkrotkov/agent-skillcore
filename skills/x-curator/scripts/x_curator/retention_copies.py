"""A canonical database receipt must contain the exact bytes of each expired copy."""
import json
import os
from pathlib import Path
from functools import lru_cache
from .retention_files import target, old


def same(root, path, body):
    target(root, str(path.relative_to(root)))
    return path.is_file() and old(path) and path.read_bytes() == body.encode()


def copies(root, folder, identity, proof):
    if proof is None:
        return []
    path = target(root, str(folder.relative_to(root)) + '/' + identity + '.jsonl')
    found = [path] if same(root, path, proof['events']) else []
    return found + sessions(root, proof)


def session_ids(proof):
    return [event['thread_id'] for line in proof['events'].splitlines()
            if (event := json.loads(line)).get('type') == 'thread.started']


def sessions(root, proof):
    home = Path(os.environ.get('CODEX_HOME', root / 'poc-20261006-codex-runtime'))
    if not home.is_absolute() or not home.is_relative_to(root):
        return []
    folder = target(root, str(home.relative_to(root)) + '/sessions')
    ids = session_ids(proof)
    if len(ids) != 1:
        return []
    return [p for p in native_index(folder).get(ids[0], ()) if same(root, p, proof['rollout'])]


@lru_cache(maxsize=1)
def native_index(folder):
    # Scan once per retention pass; rescanning for each execution is quadratic.
    index = {}
    for path in folder.rglob('*.jsonl'):
        index.setdefault(path.stem[-36:], []).append(path)
    return index
