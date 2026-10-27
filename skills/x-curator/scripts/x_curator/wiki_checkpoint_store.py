"""Seal complete indexing checkpoints only under a fresh dependency fence."""
import json
from marshal import dumps
from .publication_files import private_target
from .wiki_input_fence import verify
from . import audit_memo,proof_files,proof_revisions

IDENTITY=('wiki-checkpoint',0)


def members(db):
    return {r[0] for r in db.execute("SELECT p.id FROM publications p JOIN jobs j ON j.account=p.account AND j.id=p.source WHERE p.state='published' AND j.state='published'")}


def save(db,root,snapshot,manifest,result):
    with db:
        db.execute('BEGIN IMMEDIATE')
        verify(snapshot.reads,snapshot.stamp,snapshot)
        if members(db)!=set(snapshot.values[0]):
            return
        artifacts=snapshot.artifacts
        if not proof_files.unchanged((artifacts,)):
            raise ValueError('wiki artifacts changed before checkpoint')
        payload=dict(manifest=manifest,result=result,values=snapshot.values,packets=snapshot.packets,epoch=proof_revisions.epoch(db),
                     schema=db.execute('PRAGMA schema_version').fetchone()[0],artifacts=artifacts)
        audit_memo.retain(root,IDENTITY,(dumps(payload),snapshot.stamp[0],snapshot.stamp[1],snapshot.stamp,snapshot.reads.metadata))

def current_identity(db,root,payload):
    current=json.loads(private_target(root,'wiki/CURRENT.json').read_text())
    return current['generation']==payload['manifest']['generation'] and payload['schema']==db.execute('PRAGMA schema_version').fetchone()[0]
