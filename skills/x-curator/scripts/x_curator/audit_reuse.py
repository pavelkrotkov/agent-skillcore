"""Successful in-process proofs remain reusable only while every dependency matches."""
from collections import OrderedDict
from contextlib import contextmanager
from marshal import dumps, loads

from .read_set import ReadSet, ChangedDependencies
from . import audit_memo
from .proof_mode import FULL,MaintenanceRequired

_CACHE = OrderedDict()


def connection(db):
    while isinstance(db, ReadSet):
        db = db.db
    return db


@contextmanager
def snapshot(db):
    raw = connection(db)
    if raw.in_transaction:
        yield
    else:
        with raw:
            raw.execute('BEGIN DEFERRED')
            yield


def cached(db, root, identity, compute, required=False):
    key = connection(db), root, identity
    with snapshot(db):
        from .compact_proofs import authority, restored
        if authority(db, root, identity) is not None:
            compute = lambda reads: restored(reads, root, identity)
            required = False
        previous = previous_proof(key,root,identity,required)
        if previous:
            value, queries, files, stamp, metadata = previous
            reads = ReadSet(db)
            reads.queries, reads.files = dict(queries), dict(files)
            reads.metadata = dict(metadata)
            try:
                reads.verify(stamp)
            except (ChangedDependencies, OSError, ValueError):
                pass
            else:
                remember(key,(value,queries,files,stamp,metadata))
                return loads(value)
        reads = ReadSet(db)
        value = dumps(compute(reads))
        record = value, reads.queries, reads.files, reads.fingerprint(), reads.metadata
        remember(key,record)
        audit_memo.retain(root,identity,record)
        return loads(value)


def previous_proof(key,root,identity,required):
    diagnostic={}
    previous=None if FULL.get() else (_CACHE.pop(key,None) or audit_memo.read(root,identity,diagnostic))
    if required and previous is None and not FULL.get():
        raise MaintenanceRequired('Historical proof checkpoint unavailable; run wiki --audit --max-sources 0; '
                                  f'identity={identity!r}; failure={diagnostic!r}')
    return previous


def remember(key,record):
    # ponytail: cap at 1024 resident proofs; evictions retain signed disk reuse.
    _CACHE[key]=record
    if len(_CACHE)>1024:
        _CACHE.popitem(last=False)
