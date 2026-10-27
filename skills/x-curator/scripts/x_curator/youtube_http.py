"""All extractor requests and redirects cross the same accounted transport."""
import io
from urllib.parse import urljoin

from . import blobs, http_receipts
from .public_http import header


def open_request(db, token, request, identities):
    from yt_dlp.networking import Request, Response
    from yt_dlp.networking.exceptions import HTTPError
    request = Request(request) if isinstance(request, str) else request
    for _ in range(6):
        identity, received = http_receipts.request(db, token, request.url, request.method, request.data, dict(request.headers))
        identities.append(identity)
        response = Response(io.BytesIO(blobs.read(db, received['body_sha'])), request.url,
                            dict(received['headers']), received['status'])
        if received['status'] not in (301, 302, 303, 307, 308):
            if response.status >= 400:
                raise HTTPError(response)
            return response
        request = redirected(request, received)
    raise ValueError('YouTube redirect budget exhausted')


def redirected(request, response):
    location = header(response['headers'], 'location')
    if not location:
        raise ValueError('YouTube redirect has no location')
    request = request.copy()
    request.url = urljoin(request.url, location)
    if response['status'] == 303 or (response['status'] in (301, 302) and request.method == 'POST'):
        request.data, request.method = None, 'GET'
        request.headers.pop('Content-Type', None)
    return request
