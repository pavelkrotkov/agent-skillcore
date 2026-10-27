"""Every bounded redirect uses the same public transport and persisted request budget."""
import time
from urllib.parse import urljoin

from .quick_sources import source
from .retrievals import request
from .reuse import capture as reusable_capture
from .youtube_urls import require_text


REUSE_LIMIT = 'Retained bytes were reused without a network request; reassess authority, relevance and freshness for this item.'


def resolved(db, token, url, fetch):
    require_text(url)
    cached = reusable_capture(db, token, url)
    if cached:
        source_data = {key: cached[key] for key in ('url', 'mime', 'body_sha', 'fetched', 'reused_from', 'reused_at')}
        return source_data, [REUSE_LIMIT]
    final_url, mime, sha = retrieve(db, token, url, fetch)
    return dict(url=final_url, mime=mime, body_sha=sha, fetched=time.time()), []


def retrieve(db, token, url, fetch):
    for _ in range(4):
        source(db, token, url)
        status, mime, sha, location = request(db, token, url, fetch)
        if status == 200:
            return url, mime, sha
        if status not in (301, 302, 303, 307, 308) or not location:
            raise ValueError('quick source unavailable: HTTP ' + str(status))
        url = urljoin(url, location)
    raise ValueError('quick source exceeds three-redirect allowance')
