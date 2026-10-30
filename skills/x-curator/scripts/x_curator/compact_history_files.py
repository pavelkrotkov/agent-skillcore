"""Select aged, correctly identified model-history files inside the private state."""
import os
import time
import json
from pathlib import Path

from .retention_files import target
from .storage import sha256

def native_paths(root, sessions):
    # The shared default Codex home is outside this corpus and must never be swept.
    home = Path(os.environ.get('CODEX_HOME', root / 'poc-20261006-codex-runtime'))
    if not home.is_absolute() or not home.is_relative_to(root):
        return []
    folder = target(root, str(home.relative_to(root)) + '/sessions')
    return [p for p in folder.rglob('*.jsonl') if p.stem[-36:] in sessions and identified(root, p)]


def identified(root, path):
    # A matching filename alone is insufficient authority to discard a session.
    if not regular_aged(root, path):
        return False
    try:
        with path.open('rb') as stream:
            first = json.loads(stream.readline(1048576))
        return session_id(first) == path.stem[-36:]
    except (ValueError, OSError):
        return False


def session_id(row):
    if not isinstance(row, dict) or row.get('type') != 'session_meta':
        return None
    payload = row.get('payload')
    return payload.get('id') if isinstance(payload, dict) else None


def candidates(root, sessions, events):
    paths = set(native_paths(root, sessions))
    for relative, expected in events.items():
        path = target(root, relative)
        if path.is_file() and not path.is_symlink() and sha256(path.read_bytes()) == expected:
            paths.add(path)
    return [p for p in paths if regular_aged(root, p)]


def regular_aged(root, path):
    # Completed CLI processes can still flush their final diagnostic events.
    target(root, str(path.relative_to(root)))
    return not path.is_symlink() and path.is_file() and path.stat().st_mtime < time.time() - 300
