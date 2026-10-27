"""Only URLs registered by the controller can be read by the checker."""
from difflib import get_close_matches

from . import public_http
from .receipts import digest

GOOGLE_CONTENT = {'workspace.google.com', 'sites.google.com', 'support.google.com', 'play.google.com'}


def source(db, token, url):
    host = public_http.public_url(url).hostname.lower().rstrip('.')
    if host not in GOOGLE_CONTENT and any(host == h or host.endswith('.' + h) for h in ('bing.com', 'google.com', 'duckduckgo.com', 'search.yahoo.com', 'search.brave.com')):
        raise ValueError('search engine URLs cannot be read as sources')
    identity = digest(url)
    with db:
        db.execute('INSERT OR IGNORE INTO quick_sources VALUES(?,?,?)', (token, identity, url))
    return identity

def register(db, token, evidence):
    urls = {url for c in evidence['captures'].values() for url in c.get('required_urls', [])}
    result = {}
    for url in sorted(urls):
        try:
            result[source(db, token, url)] = url
        except ValueError:
            continue
    return result

def unknown_source(db, token, identity):
    known = dict(db.execute('SELECT url,id FROM quick_sources WHERE token=?', (token,)))
    matches = get_close_matches(identity, known, n=1)
    if matches:
        return 'Unknown source. Retry with registered source ID ' + known[matches[0]] + '. Capture IDs are citation handles, not read source IDs.'
    return 'Unknown source. Use an exact observed URL or registered source ID; capture IDs are citation handles, not read source IDs.'


def registered(db, token, identity):
    row = db.execute('SELECT url FROM quick_sources WHERE token=? AND (id=? OR url=?)', (token, identity, identity)).fetchone()
    if row is None:
        raise ValueError(unknown_source(db, token, identity))
    return row['url']
