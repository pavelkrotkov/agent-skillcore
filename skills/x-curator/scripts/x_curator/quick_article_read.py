"""Expose short article excerpts without making another network request."""
from .quick_articles import identity, entity, derive

def read(db, token, url, match):
    if not identity(url):
        return None
    from .evidence import bundle, save_capture
    evidence = bundle(db, token)
    parents = [(key, parent) for key, parent in evidence['captures'].items()
               if parent['kind'] == 'x_detail' and entity(db, parent).get('rest_id') == identity(url)]
    if not parents:
        raise ValueError('requested article has no matching authenticated focal body; title/preview is not body evidence')
    key, parent = max(parents, key=lambda item: item[1]['fetched'])
    text = entity(db, parent).get('plain_text') or ''
    start = max(0, text.find(match) - 2000)
    payload = derive(db, evidence, key, url, start)
    return dict(capture=save_capture(db, token, payload), evidence=payload)
