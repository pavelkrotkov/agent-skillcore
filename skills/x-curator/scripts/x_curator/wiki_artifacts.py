"""Reuse authenticated artifact/link validation while every file identity is unchanged."""
from marshal import dumps,loads
from . import audit_memo,proof_files,wiki_links
from .receipts import digest
from .proof_mode import FULL


def verify(root,manifest,links=False):
    previous=prior(root,manifest)
    metadata=files(root,manifest,previous[4] if previous else {})
    linked=bool(previous and loads(previous[0])[1])
    if links and not linked:
        wiki_links.validate(root/'wiki/builds'/manifest['generation']/'site',root)
        linked=True
    record=(dumps((digest(manifest),linked)),{},{},({},{}),metadata)
    if record!=previous:
        audit_memo.retain(root,('wiki-artifacts',manifest['generation']),record)
    return metadata


def prior(root,manifest):
    record=None if FULL.get() else audit_memo.read(root,('wiki-artifacts',manifest['generation']))
    return record if record and loads(record[0])[0]==digest(manifest) else None


def files(root,manifest,previous):
    metadata,namespace={},{}
    for name,expected in manifest['files'].items():
        file=str(root),name
        actual,metadata[file]=proof_files.checked(file,bytes.fromhex(expected),previous.get(file),namespace,full=FULL.get())
        if actual.hex()!=expected:
            raise ValueError('wiki artifact readback failed: '+name)
    return metadata
