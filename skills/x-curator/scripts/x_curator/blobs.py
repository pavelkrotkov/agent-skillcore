"""Private content-addressed acquisition bytes, shared by readers and model inputs."""
from pathlib import Path

from .publication_files import write_verified
from .storage import sha256
from .read_set import read_file


def state_root(db):
    return Path(db.execute("PRAGMA database_list").fetchone()[2]).parent


def put(db, body):
    identity = sha256(body)
    write_verified(state_root(db), "blobs/" + identity, body)
    return identity


def read(db, identity):
    if len(identity) != 64 or any(c not in "0123456789abcdef" for c in identity):
        raise ValueError("invalid acquisition blob identity")
    body = read_file(db, state_root(db), "blobs/" + identity)
    if sha256(body) != identity:
        raise ValueError("tampered acquisition blob")
    return body


def verify_payload(db, payload):
    identities = payload.get("images", []) + [payload.get("body_sha")]
    for identity in filter(None, identities):
        read(db, identity)
    if payload.get('kind') == 'pdf':
        from .pdf_schema import verify_pixels
        verify_pixels(db, payload)
