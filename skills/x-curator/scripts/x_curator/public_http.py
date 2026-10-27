"""Bounded public retrieval pins the validated address through the TLS connection."""
import http.client
import ipaddress
import socket
from urllib.parse import urlsplit


MAX_BYTES = 128 * 1024 * 1024


def destination(url):
    parts = public_url(url)
    port = parts.port or (443 if parts.scheme == "https" else 80)
    addresses = socket.getaddrinfo(parts.hostname, port, type=socket.SOCK_STREAM)
    if not addresses or not all(ipaddress.ip_address(a[4][0]).is_global for a in addresses):
        raise ValueError("private or reserved network destination rejected")
    return parts, port, addresses[0][4][0]


def public_url(url):
    parts = urlsplit(url)
    if parts.scheme not in ("https", "http") or not parts.hostname:
        raise ValueError("public HTTP URL required")
    if parts.username is not None or parts.password is not None:
        raise ValueError("credential-bearing URLs are not public evidence")
    return parts


def fetch(url):
    status, headers, body = exchange(url)
    headers = dict((key.lower(), value) for key, value in headers)
    return status, headers.get('content-type', ''), body, headers.get('location')


def exchange(url, method='GET', body=None, headers=None, max_bytes=MAX_BYTES, allow_prefix=False):
    if method not in ('GET', 'POST') or not isinstance(body, (bytes, type(None))):
        raise ValueError('unsupported public request')
    if not 0 < max_bytes <= MAX_BYTES:
        raise ValueError('invalid public response byte limit')
    return transmit(url, method, body, request_headers(headers), max_bytes, allow_prefix)


def request_headers(headers):
    headers = {key.lower(): value for key, value in (headers or {}).items()}
    forbidden = {'authorization', 'proxy-authorization', 'cookie', 'host', 'connection', 'transfer-encoding', 'content-length'}
    # The controller owns authority, framing and authentication. Extractor-supplied overrides
    # could bypass the pinned destination or send private credentials to a public endpoint.
    if forbidden.intersection(key.lower() for key in headers):
        raise ValueError('public request contains controlled or credential headers')
    headers['accept-encoding'] = 'identity'
    headers.setdefault('user-agent', 'XCurator/1.0 source research')
    return headers


def transmit(url, method, data, headers, max_bytes, allow_prefix=False):
    parts, port, address = destination(url)
    factory = http.client.HTTPSConnection if parts.scheme == "https" else http.client.HTTPConnection
    connection = factory(parts.hostname, port, timeout=30)
    # Keep hostname/SNI validation, but never perform a second DNS lookup after validation.
    connection._create_connection = lambda _, timeout, source=None: socket.create_connection((address, port), timeout, source)
    try:
        target = parts.path or "/"
        if parts.query:
            target += "?" + parts.query
        connection.request(method, target, body=data, headers=headers)
        response = connection.getresponse()
        body = response.read(max_bytes + 1)
        if len(body) > max_bytes and not allow_prefix:
            raise ValueError("source exceeds acquisition byte budget")
        return response.status, response.getheaders(), body
    finally:
        connection.close()


def header(headers, name):
    values = [value for key, value in headers if key.lower() == name]
    if len(values) > 1:
        raise ValueError('ambiguous HTTP header: ' + name)
    return values[0] if values else None
