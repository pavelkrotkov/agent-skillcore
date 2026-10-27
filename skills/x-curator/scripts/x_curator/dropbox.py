"""Dropbox shared PDFs use its documented download route, retaining link parameters."""
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


def download_url(url):
    parts = urlsplit(url)
    if parts.scheme != 'https' or parts.netloc not in ('dropbox.com', 'www.dropbox.com'):
        return None
    if not parts.path.startswith(('/scl/fi/', '/s/')) or not parts.path.lower().endswith('.pdf'):
        return None
    query = [(key, value) for key, value in parse_qsl(parts.query, keep_blank_values=True) if key not in ('dl', 'raw')]
    return urlunsplit(parts._replace(query=urlencode(query + [('dl', '1')])))


def validate(mime, body):
    if mime.split(';')[0].strip().lower() not in ('application/pdf', 'application/binary', 'application/octet-stream') or not body.startswith(b'%PDF-'):
        raise ValueError('Dropbox shared PDF download did not return a PDF response')


def reusable(payload):
    if not payload or payload.get('pdf_download'):
        return payload
    if download_url(payload['url']) or download_url(payload['final_url']):
        return None
    return payload


def reader_mime(payload, body):
    mime = payload['mime'].split(';')[0].strip().lower()
    if payload.get('pdf_download') or download_url(payload['url']):
        validate(mime, body)
        return 'application/pdf'
    return mime
