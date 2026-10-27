"""Native complete epochs reuse row proofs; every activation still checks file identity."""
from . import proof_revisions,proof_files
from .audit_reuse import connection


def verify(reads,stamp,snapshot=None):
    current=proof_revisions.epoch(connection(reads)) if snapshot is not None else None
    if snapshot is None or current is None or current!=snapshot.epoch or not same_files(reads):
        reads.verify(stamp)
    if snapshot is not None:
        snapshot.epoch=current


def same_files(reads):
    return reads.files.keys()<=reads.metadata.keys() and proof_files.unchanged((reads.metadata,))


def bound_current(snapshot):
    from .wiki_current import current
    from .wiki_files import activate
    from .audit_reuse import snapshot as transaction
    sources,runs,pages=snapshot.values
    reads,stamp=snapshot.check(snapshot.db,snapshot.root,sources,pages,runs)
    try:
        with transaction(snapshot.db):
            verify(reads,stamp,snapshot)
            return current(snapshot.db,snapshot.root,sources,pages)
    except (ValueError,OSError,KeyError,TypeError,RuntimeError):
        activate(snapshot.root,None)
        raise
