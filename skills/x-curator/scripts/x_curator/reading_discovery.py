"""Oversized sources get primary-source discovery from explicitly limited context."""
from .codex_profile import MODEL
from .evidence import bundle
from .executions import execute, recorded
from .reading_work import required
from .receipts import digest


def discover(db, token, call):
    evidence = bundle(db, token)
    if not required(evidence):
        return execute(db, token, 'discover', MODEL, call)
    context = {key: capture for key, capture in evidence['captures'].items()
               if capture['kind'] in ('selection', 'x_detail') and len(str(capture)) <= 50000}
    view = {'account': evidence['account'], 'source': evidence['source'], 'captures': context,
            'discovery_view_of': digest(evidence),
            'unread_sources': [{'url': c['url'], 'kind': c['kind'], 'text_chars': len(c.get('text', ''))}
                               for key, c in evidence['captures'].items() if key not in context]}
    request = dict(role='discover', bundle=view, bundle_sha=digest(view), proposal=None)
    return recorded(db, token, 'discover', MODEL, call, request)
