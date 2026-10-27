"""Later retained negative or conflicting evidence vetoes a stale response reuse."""
from . import blobs, x_detail
from .receipts import digest
from .revisions import scrub
from .x_urls import identity


def superseded(db, evidence, requested, fetched, at, focal):
    rows = db.execute('''SELECT url,status,body_sha FROM retrievals WHERE account=? AND source=?
        AND finished>? AND finished<=?''', (evidence['account'], evidence['source'], fetched, at))
    return any(conflicts(db, row, requested, focal) for row in rows if identity(row['url']))


def conflicts(db, row, requested, focal):
    if row['status'] != 200:
        return identity(row['url']) == requested
    body = blobs.read(db, row['body_sha'])
    try:
        newer, _ = x_detail.validate(body, requested)
    except x_detail.AmbiguousPost:
        return True
    except (ValueError, KeyError, TypeError):
        return identity(row['url']) == requested
    return digest(scrub(newer)) != digest(scrub(focal))


def usable(db, evidence, payload, at):
    if payload['kind'] != 'x_detail':
        return payload
    requested = identity(payload['final_url'])
    if not requested:
        return None
    focal, _ = x_detail.validate(blobs.read(db, payload['body_sha']), requested)
    if not superseded(db, evidence, requested, payload['fetched'], at, focal):
        return payload
    return None
