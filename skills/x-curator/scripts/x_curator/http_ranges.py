"""Strict byte intervals require a stable strong representation validator."""
from email.utils import parsedate_to_datetime
import re

from .public_http import header

WIDTH = 1048576


def validator(headers):
    tag = header(headers, 'etag')
    if tag is not None:
        if not re.fullmatch(r'"[\x21\x23-\x7e\x80-\xff]*"', tag):
            raise ValueError('range response needs a strong ETag')
        return ['etag', tag]
    modified, date = header(headers, 'last-modified'), header(headers, 'date')
    if not modified or not date:
        raise ValueError('range response has no strong validator')
    # A conservative date separation avoids treating same-second modifications as a strong validator.
    if parsedate_to_datetime(date).timestamp() - parsedate_to_datetime(modified).timestamp() < 60:
        raise ValueError('Last-Modified validator is too recent')
    return ['last-modified', modified]


def validate(response, start, size, expected):
    length = min(WIDTH, size - start)
    headers = response['headers']
    if response['status'] != 206 or header(headers, 'content-range') != f'bytes {start}-{start + length - 1}/{size}':
        raise ValueError('range interval differs from requested representation')
    if header(headers, 'content-length') != str(length) or header(headers, 'content-encoding') not in (None, 'identity'):
        raise ValueError('range length or encoding differs')
    current = validator(headers)
    if expected is not None and current != expected:
        raise ValueError('range representation changed')
    return current
