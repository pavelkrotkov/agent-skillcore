"""Each public RSS query consumes one controller reservation before transport."""
from urllib.parse import urlencode
import xml.etree.ElementTree as ET

from . import blobs, quick_store, quick_window
from .quick_web import fetch
from .quick_sources import source
from .retrievals import request


@quick_window.bounded
def search(db, token, query):
    if not isinstance(query, str) or not 1 <= len(query.strip()) <= 500:
        raise ValueError('one bounded search query required')
    quick_store.reserve_search(db, token)
    url = 'https://www.bing.com/search?' + urlencode({'format': 'rss', 'q': query})
    status, _, sha, _ = request(db, token, url, fetch)
    if status != 200:
        raise ValueError('search unavailable: HTTP ' + str(status))
    root = ET.fromstring(blobs.read(db, sha))
    if root.tag != 'rss':
        raise ValueError('search feed unavailable')
    found = []
    for item in root.findall('./channel/item')[:10]:
        try:
            identity = source(db, token, item.findtext('link'))
        except ValueError:
            continue
        found.append(dict(source=identity, title=item.findtext('title', '')[:500],
                          snippet=item.findtext('description', '')[:1500]))
    return found
