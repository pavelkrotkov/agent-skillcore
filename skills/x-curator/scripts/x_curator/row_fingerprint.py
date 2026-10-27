"""Frame SQLite scalar bytes without copying receipt blobs into escaped text."""
import hashlib


def row_digest(rows):
    digest = hashlib.sha256()
    for row in rows:
        digest.update(len(row).to_bytes(8, 'big'))
        for value in row:
            body = value if isinstance(value, bytes) else value.encode() if isinstance(value, str) else repr(value).encode()
            digest.update(type(value).__name__.encode() + b'\0')
            digest.update(len(body).to_bytes(8, 'big'))
            digest.update(body)
    return digest.digest()


def query_stamp(db, query):
    from .read_set import ReadSet
    from .proof_revisions import stamp
    if isinstance(db, ReadSet):
        return db.query_stamp(query)
    return stamp(db,query)
