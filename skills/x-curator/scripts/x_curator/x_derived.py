"""Derive requested posts from proven responses without inventing HTTP requests."""
import time

from .x_derived_receipts import derive
from .x_response_conflicts import usable
from .x_urls import identity


def find(db, evidence, url, cached=None):
    try:
        cached = usable(db, evidence, cached, time.time()) if cached else None
    except (ValueError, KeyError, TypeError, OSError):
        cached = None
    if cached:
        return cached
    candidates = [candidate(db, evidence, key, parent, url, time.time())
                  for key, parent in evidence['captures'].items()] if identity(url) else []
    return newest(list(filter(None, candidates)))


def newest(candidates):
    if not candidates:
        return None
    latest = max(item[0]['fetched'] for item in candidates)
    current = [item for item in candidates if item[0]['fetched'] == latest]
    if len({fingerprint for _, fingerprint in current}) != 1:
        return None
    return current[0][0]


def candidate(db, evidence, key, parent, url, at):
    try:
        return derive(db, evidence, key, parent, url, at)
    except (ValueError, KeyError, TypeError, OSError):
        return None


def verify(db, evidence):
    for payload in evidence['captures'].values():
        if 'derived_from' in payload:
            parent = evidence['captures'][payload['derived_from']]
            expected, _ = derive(db, evidence, payload['derived_from'], parent,
                                 payload['url'], payload['derived_at'])
            if payload != expected:
                raise ValueError('derived post differs from its authenticated response')
