"""Reconstruct derived focal evidence from its immutable parent and HTTP receipt."""
from . import blobs, x_detail, x_response_conflicts
from .receipts import digest
from .revisions import scrub
from .x_urls import identity


def derive(db, evidence, key, parent, url, at):
    if parent['kind'] != 'x_detail' or 'derived_from' in parent:
        raise ValueError('derived posts require an original detail response')
    if not 0 <= at - parent['fetched'] <= 86400:
        raise ValueError('derived post response is stale')
    requested = identity(url)
    if requested in (None, evidence['source']):
        raise ValueError('derived evidence requires a valid context-post URL')
    body = blobs.read(db, parent['body_sha'])
    focal, _ = x_detail.validate(body, requested)
    receipt = retrieval(db, evidence, parent)
    if x_response_conflicts.superseded(db, evidence, requested, parent['fetched'], at, focal):
        raise x_detail.AmbiguousPost('a newer retained response contradicts the focal')
    payload = {name: parent[name] for name in ('final_url', 'mime', 'body_sha', 'fetched')}
    payload.update(url=url, focal_id=requested, derived_from=key,
                   derivation_retrieval=receipt, derived_at=at)
    payload.update(x_detail.extract(body, requested, parent['thread_scope']))
    return payload, digest(scrub(focal))


def retrieval(db, evidence, parent):
    row = db.execute('''SELECT id FROM retrievals WHERE account=? AND source=? AND url=?
        AND body_sha=? AND status=200 AND error IS NULL AND finished<=?
        ORDER BY finished DESC,id LIMIT 1''', (evidence['account'], evidence['source'],
        parent['final_url'], parent['body_sha'], parent['fetched'])).fetchone()
    if row is None or not identity(parent['final_url']):
        raise ValueError('derived post lacks an authenticated detail retrieval')
    return row['id']
