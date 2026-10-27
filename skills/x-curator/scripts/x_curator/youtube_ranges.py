"""Download only contiguous ranges from one retained direct stream URL."""
from . import blobs, http_receipts
from .http_ranges import WIDTH, validate
from .youtube_media import media_format


def acquire(db, token, value):
    value = media_format(value)
    expected, chunks, receipts = None, [], []
    for start in range(0, value['filesize'], WIDTH):
        headers = range_headers(start, value['filesize'], expected)
        identity, response = http_receipts.request(db, token, value['url'], headers=headers, max_bytes=WIDTH)
        expected = validate(response, start, value['filesize'], expected)
        body = blobs.read(db, response['body_sha'])
        if len(body) != min(WIDTH, value['filesize'] - start):
            raise ValueError('range body is truncated')
        chunks.append(body)
        receipts.append(identity)
    return dict(format=value, receipts=receipts, body_sha=blobs.put(db, b''.join(chunks)))


def range_headers(start, size, expected):
    headers = {'Range': f'bytes={start}-{min(start + WIDTH, size) - 1}'}
    if expected:
        headers['If-Range'] = expected[1]
    return headers
