"""Reuse verified bytes only while inode, ctime and namespace remain unchanged."""
import hashlib
import os
from .proof_namespace import target,identity


def metadata(file,cache):
    return identity(os.stat(target(file,cache),follow_symlinks=False))


def read(file,cache):
    before=metadata(file,cache)
    with os.fdopen(os.open(target(file,cache),os.O_RDONLY|os.O_NOFOLLOW),'rb') as stream:
        if identity(os.fstat(stream.fileno()))!=before:
            raise ValueError('proof file replaced before read')
        body=stream.read()
        if identity(os.fstat(stream.fileno()))!=before or metadata(file,cache)!=before:
            raise ValueError('proof file changed during read')
    return body,before


def checked(file,expected,prior,cache,full=False):
    if not full and prior is not None and metadata(file,cache)==prior:
        return expected,prior
    body,stamp=read(file,cache)
    return hashlib.sha256(body).digest(),stamp


def fingerprints(reads):
    from .read_set import ReadSet
    from .proof_mode import FULL
    hashes,stamps={},{}
    for file,expected in reads.files.items():
        prior=expected,reads.metadata.get(file)
        if isinstance(reads.db,ReadSet):
            hashes[file],stamps[file]=reads.db.file_stamp(file,prior),reads.db.metadata[file]
        else:
            hashes[file],stamps[file]=checked(file,*prior,reads.namespace,full=FULL.get())
    return hashes,stamps



def unchanged(groups):
    namespace={}
    return all(metadata(file,namespace)==expected for group in groups for file,expected in group.items())
