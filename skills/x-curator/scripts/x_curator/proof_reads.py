"""Record consumed file bytes and verified file identity on proof read sets."""
import hashlib
from pathlib import Path
from . import proof_files
from .proof_mode import FULL


def record_file(self, root, relative):
    from .read_set import ChangedDependencies
    observed = {}
    body = read_file(self.db, root, relative, observed, self.namespace)
    identity = str(Path(root).resolve()), relative
    stamp = hashlib.sha256(body).digest()
    if identity in self.files and self.files[identity] != stamp:
        raise ChangedDependencies('publication file changed during verification')
    self.files[identity] = stamp
    self.metadata[identity] = observed['stamp']
    return body


def stamp_file(self, file, verified=None):
    if self.shared and file in self.files:
        return self.files[file]
    if verified is None:
        self.read_file(*file)
    else:
        self.files[file],self.metadata[file] = proof_files.checked(
            file,*verified,self.namespace,full=FULL.get())
    return self.files[file]


def read_file(db, root, relative, observed=None, namespace=None):
    from .read_set import ReadSet
    if isinstance(db, ReadSet):
        body=db.read_file(root, relative)
        stamp=db.metadata[str(Path(root).resolve()),relative]
    else:
        body,stamp=proof_files.read((root,relative),namespace if namespace is not None else {})
    if observed is not None:
        observed['stamp']=stamp
    return body
