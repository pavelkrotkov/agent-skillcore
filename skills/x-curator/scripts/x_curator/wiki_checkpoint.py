"""Authenticated checkpoints skip unchanged indexing, never unknown dependency changes."""
from marshal import loads
from . import audit_memo,proof_files,proof_revisions
from .proof_mode import FULL

from .wiki_checkpoint_store import IDENTITY,save,members,current_identity


def restore(db,root):
    if FULL.get() or not (record:=audit_memo.read(root,IDENTITY)):
        return None
    try:
        with db:
            db.execute('BEGIN IMMEDIATE')
            return checked(db,root,record)
    except (ValueError,OSError,KeyError,TypeError):
        return None


def checked(db,root,record):
    from .wiki_input_load import Snapshot
    payload=loads(record[0])
    if not current_identity(db,root,payload):
        return None
    snapshot=Snapshot(db,root,retained=(payload,record))
    if payload['epoch'] is None or payload['epoch']!=proof_revisions.epoch(db):
        snapshot.reads.verify(snapshot.stamp)
    if not proof_files.unchanged((record[4],payload['artifacts'])):
        return None
    snapshot.epoch=proof_revisions.epoch(db)
    snapshot.artifacts=payload['artifacts']
    snapshot.previous_verified=True
    live=members(db)
    if live!=set(snapshot.values[0]):
        from .wiki_delta import append
        return append(snapshot,live)
    return snapshot,payload['result']
