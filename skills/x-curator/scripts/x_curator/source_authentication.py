"""Reuse parsed authentic timeline membership only for identical response bytes."""
import json
from functools import lru_cache
from .storage import sha256
from .receipts import digest
from .timeline import parse


@lru_cache(maxsize=8)
def authentic_items(body, kind):
    return frozenset((identity, availability, digest(entry)) for identity, availability, entry in parse(body, kind)[0])


def authentic_entry(row, source):
    if row is None or sha256(row['body']) != row['sha256']:
        raise ValueError('missing or tampered acquisition receipt')
    entry = json.loads(row['entry'])
    if (source, row['availability'], digest(entry)) not in authentic_items(row['body'], row['kind']):
        raise ValueError('selection does not match authentic response')
    return entry
