"""Recognize public, single-video YouTube references."""
import re
from urllib.parse import parse_qs, urlsplit


def video_id(url):
    parts = urlsplit(url)
    if parts.hostname == 'youtu.be':
        value = parts.path.lstrip('/')
    elif parts.hostname in ('youtube.com', 'www.youtube.com', 'm.youtube.com'):
        value = path_id(parts)
    else:
        return None
    validate_url(parts)
    if not re.fullmatch('[A-Za-z0-9_-]{11}', value):
        raise ValueError('single YouTube video required')
    return value


def path_id(parts):
    if parts.path == '/watch':
        values = parse_qs(parts.query, keep_blank_values=True).get('v', [])
        if len(values) == 1:
            return values[0]
    match = re.fullmatch(r'/(?:shorts|embed|live)/([A-Za-z0-9_-]{11})', parts.path)
    if match:
        return match[1]
    raise ValueError('unrecognized or ambiguous YouTube video reference')


def validate_url(parts):
    if parts.scheme != 'https' or parts.username or parts.password or parts.port not in (None, 443):
        raise ValueError('public HTTPS YouTube URL required')


def require_text(url):
    if video_id(url):
        raise ValueError('quick checks read HTML/plain text only; media needs explicit research approval')
