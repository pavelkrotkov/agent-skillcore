"""Bounded mismatch details contain component names and digests, never evidence bodies."""
from itertools import zip_longest
from .storage import sha256

MISSING = object()


def require_prompt(users, expected):
    matches = sum(sha256(part.get('text', '').encode()) == expected for part in users)
    if matches != 1:
        raise ValueError(f'complete original model prompt not retained exactly once; matches={matches}')


def require_receipt(actual, expected):
    names = ('input_sha', 'output_sha', 'log_sha', 'session', 'answer', 'semantic_role')
    failed = [name for name, observed, retained in zip(names, actual, expected) if observed != retained]
    if failed:
        raise ValueError('tampered execution receipt: ' + ','.join(failed))


def hash_label(value):
    if value is MISSING:
        return 'missing'
    valid = isinstance(value, str) and len(value) == 64 and all(c in '0123456789abcdef' for c in value)
    return value if valid else 'invalid'


def image_mismatch(actual, expected, version):
    if not isinstance(expected, list):
        return 'expected image list has type ' + type(expected).__name__
    index, (observed, retained) = next((index, pair) for index, pair in enumerate(
        zip_longest(actual, expected, fillvalue=MISSING)) if pair[0] != pair[1])
    version = version.removeprefix('x-curator-input-proof-')
    return (f'version={version}; counts={len(actual)}/{len(expected)}; index={index}; '
            f'actual={hash_label(observed)}; expected={hash_label(retained)}')
