"""Only known HTTPS post URLs qualify for authenticated X detail retrieval."""
import re
from urllib.parse import urlsplit

from . import public_http


def focal_id(payload):
    return payload.get('focal_id') or identity(payload['final_url'])


def identity(url):
    parts = urlsplit(url)
    if parts.scheme != 'https' or parts.netloc not in ('x.com', 'twitter.com', 'www.x.com', 'www.twitter.com'):
        return None
    match = re.fullmatch(r"/(?:i|[A-Za-z0-9_]+)/status/([0-9]+)/?", parts.path)
    return match[1] if match else None


def source_fetcher(client):
    def fetch(url):
        requested = identity(url)
        if requested:
            status, body = client.detail(requested)
            return status, "application/json", body, None
        return public_http.fetch(url)
    return fetch

def article_identity(url):
    parts = urlsplit(url)
    match = re.fullmatch(r'/i/article/(\d+)/?', parts.path)
    return match[1] if parts.netloc in ('x.com', 'www.x.com', 'twitter.com', 'www.twitter.com') and parts.scheme == 'https' and match else None
