"""Signed compressed data replaces transcripts, never source evidence or approval checks."""
import hmac
import zlib
from marshal import dumps, loads

from .audit_key import secret
from .proof_mode import MaintenanceRequired


def pack(root, context, record, *, authority=None):
    body = zlib.compress(dumps(record), level=9)
    key = controller_key(root, authority is None)
    if authority is not None:
        require_signature(key, *authority)
    return body, hmac.digest(key, context + body, 'sha256')


def unpack(root, context, body, signature):
    require_signature(controller_key(root, False), context, body, signature)
    return decode(body)


def require_signature(key, context, body, signature):
    expected = hmac.digest(key, context + body, 'sha256')
    if not hmac.compare_digest(expected, signature):
        raise MaintenanceRequired('Compact approval signature changed; restore the proof and controller key')


def controller_key(root, create_missing):
    try:
        return secret(root, create_missing=create_missing)
    except (OSError, ValueError) as exc:
        raise MaintenanceRequired('Compact approval controller key unavailable; restore the original key') from exc


def decode(body):
    try:
        record = loads(zlib.decompress(body))
        if record['version'] != 1:
            raise ValueError('unsupported compact approval version')
        return record
    except (ValueError, KeyError, TypeError, EOFError, zlib.error) as exc:
        raise MaintenanceRequired('Compact approval cannot be decoded; restore its original bytes') from exc
