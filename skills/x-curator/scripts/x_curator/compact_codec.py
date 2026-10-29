"""Signed compressed data replaces transcripts, never source evidence or approval checks."""
import hmac
import zlib
from marshal import dumps, loads

from .audit_key import secret
from .proof_mode import MaintenanceRequired


def pack(root, context, record):
    body = zlib.compress(dumps(record), level=9)
    return body, hmac.digest(secret(root), context + body, 'sha256')


def unpack(root, context, body, signature):
    try:
        expected = hmac.digest(secret(root, create_missing=False), context + body, 'sha256')
    except (OSError, ValueError) as exc:
        raise MaintenanceRequired('Compact approval controller key unavailable; restore the original key') from exc
    if not hmac.compare_digest(expected, signature):
        raise MaintenanceRequired('Compact approval signature changed; restore the proof and controller key')
    return decode(body)


def decode(body):
    try:
        record = loads(zlib.decompress(body))
        if record['version'] != 1:
            raise ValueError('unsupported compact approval version')
        return record
    except (ValueError, KeyError, TypeError, EOFError, zlib.error) as exc:
        raise MaintenanceRequired('Compact approval cannot be decoded; restore its original bytes') from exc
