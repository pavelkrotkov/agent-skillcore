"""Reuse only verified acquisitions from this fresh corpus and the same source revision."""
import time

from .evidence import current_bundle
from .leases import require_lease


def captures(db, token, max_age=86400):
    job = require_lease(db, token, time.time())
    attempts = db.execute('SELECT token FROM attempts WHERE account=? AND id=? AND token!=? ORDER BY started DESC',
                          (job['account'], job['id'], token)).fetchall()
    selected = {}
    now = time.time()
    for row in attempts:
        previous = verified(db, job, row[0])
        for identity, payload in previous.items():
            if reusable(payload, now, max_age):
                selected.setdefault(payload['url'], (identity, payload))
    return {url: dict(payload, reused_from=identity, reused_at=now)
            for url, (identity, payload) in selected.items()}


def capture(db, token, url, max_age=86400):
    job = require_lease(db, token, time.time())
    rows = db.execute('''SELECT DISTINCT a.token,a.id FROM attempts a JOIN quick_sources s ON s.token=a.token
        WHERE a.account=? AND a.token!=? AND s.url=? ORDER BY a.started DESC''',
                      (job['account'], token, url)).fetchall()
    now = time.time()
    for row in rows:
        previous = verified(db, {'account': job['account'], 'id': row['id']}, row['token'])
        for identity, payload in previous.items():
            if payload.get('quick_excerpt') and url in (payload.get('requested_url'), payload.get('url')) and reusable(payload, now, max_age):
                return dict(payload, reused_from=identity, reused_at=now)
    return None


def reusable(payload, now, max_age):
    return payload['kind'] not in ('selection', 'unavailable') and 'derived_from' not in payload and 0 <= now - payload['fetched'] <= max_age


def verified(db, job, token):
    try:
        return current_bundle(db, job, token)['captures']
    except (ValueError, KeyError, TypeError, OSError):
        return {}
