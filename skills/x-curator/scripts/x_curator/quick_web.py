"""Budgeted searches and registered, bounded text excerpts; never full-media readers."""
from . import blobs, public_http, quick_redirects, quick_sources, quick_window, quick_article_read
from .evidence import save_capture
from .html_evidence import read as html
from .youtube_urls import require_text


PREFIX_BYTES = 1_048_576


def fetch(url):
    status, headers, body = public_http.exchange(url, max_bytes=PREFIX_BYTES, allow_prefix=True)
    return status, public_http.header(headers, 'content-type') or '', body, public_http.header(headers, 'location')


@quick_window.bounded
def read(db, token, identity, match=''):
    url = quick_sources.registered(db, token, identity)
    if not isinstance(match, str) or len(match) > 200:
        raise ValueError('match must be a literal string of at most 200 characters')
    article = quick_article_read.read(db, token, url, match)
    if article:
        return article
    source, reuse_limits = quick_redirects.resolved(db, token, url, fetch)
    require_text(source['url'])
    body = blobs.read(db, source['body_sha'])
    extracted = text(body[:PREFIX_BYTES], source['mime'], source['url'])
    start = max(0, extracted['text'].find(match) - 2000)
    payload = dict(extracted, **source, requested_url=url, text=extracted['text'][start:start + 6000], excerpt_start=start,
                   quick_excerpt=True, truncated=len(body) > PREFIX_BYTES,
                   limitations=extracted.get('limitations', []) + [f'Parsed at most the first {PREFIX_BYTES} bytes; truncated marks a retained lookahead byte. The rest of the resource was not reviewed.'] + reuse_limits)
    return {'capture': save_capture(db, token, payload), 'evidence': payload}


def text(body, mime, url):
    kind = mime.split(';')[0].lower()
    if kind in ('text/html', 'application/xhtml+xml'):
        return html(body, url)
    if kind == 'text/plain':
        return {'kind': 'text', 'text': body.decode('utf-8', errors='replace')}
    raise ValueError('quick checks read HTML/plain text only; media needs explicit research approval')
