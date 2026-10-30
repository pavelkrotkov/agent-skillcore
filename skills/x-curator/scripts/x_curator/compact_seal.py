"""Permanent controller attestations; authenticate before decoding private proof data."""
from . import compact_codec
from .receipts import encoded

TABLE = 'compact_approvals'
KINDS = ('publication', 'mapping', 'diagnostic')


def initialize(db):
    db.execute('''CREATE TABLE IF NOT EXISTS compact_approvals (
        kind TEXT NOT NULL, identity TEXT NOT NULL, body BLOB NOT NULL,
        signature BLOB NOT NULL, active INTEGER NOT NULL DEFAULT 0,
        PRIMARY KEY(kind,identity))''')


def present(db):
    return db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (TABLE,)).fetchone() is not None


def context(root, identity):
    return encoded(['compact-approval/v1', str(root.resolve()), identity])


def write(db, root, identity, record, active):
    prior = db.execute('SELECT kind,identity,body,signature FROM compact_approvals LIMIT 1').fetchone()
    authority = None if prior is None else (context(root, tuple(prior[:2])), prior[2], prior[3])
    body, signature = compact_codec.pack(root, context(root, identity), record, authority=authority)
    db.execute('''INSERT INTO compact_approvals VALUES (?,?,?,?,?)
        ON CONFLICT(kind,identity) DO UPDATE SET body=excluded.body,
        signature=excluded.signature,active=excluded.active''', (*identity, body, signature, active))


def read(db, root, identity, pending=False):
    if identity[0] not in KINDS or not present(db):
        return None
    row = db.execute('SELECT body,signature,active FROM compact_approvals WHERE kind=? AND identity=?', identity).fetchone()
    if row is None or (not row[2] and not pending):
        return None
    return compact_codec.unpack(root, context(root, identity), row[0], row[1])
