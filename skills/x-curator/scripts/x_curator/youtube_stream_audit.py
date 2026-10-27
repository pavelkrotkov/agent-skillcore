"""Reconstruct complete stream hashes from ordered, owned HTTP receipts."""
from . import blobs, http_receipts, youtube_ranges
from .http_ranges import validate
from .youtube_media import media_format
from .storage import sha256


def verify_stream(db, stream, job):
    value = media_format(stream['format'])
    expected, bodies, start = None, [], 0
    for identity in stream['receipts']:
        sent, response = http_receipts.read(db, identity, job)
        wanted = youtube_ranges.range_headers(start, value['filesize'], expected)
        if (sent['url'], sent['method'], sent['headers']) != (value['url'], 'GET', wanted):
            raise ValueError('YouTube range request differs from assembly order')
        expected = validate(response, start, value['filesize'], expected)
        body = blobs.read(db, response['body_sha'])
        if len(body) != min(youtube_ranges.WIDTH, value['filesize'] - start):
            raise ValueError('YouTube range body is truncated')
        bodies.append(body)
        start += len(body)
    if start != value['filesize'] or sha256(b''.join(bodies)) != stream['body_sha']:
        raise ValueError('YouTube assembly has gaps or differs from retained chunks')
    blobs.read(db, stream['body_sha'])
