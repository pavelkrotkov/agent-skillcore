"""Controller-owned key bytes and permissions come from the same regular-file descriptor."""
import os
import stat
from .publication_files import private_target


def secret(root, *, create_missing=True):
    path = private_target(root, 'audit-memos/key')
    if create_missing:
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        create(path)
    with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW), 'rb') as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise ValueError('controller-owned private audit-memo key required')
        key = stream.read(33)
    if len(key) != 32:
        raise ValueError('private audit-memo key required')
    return key


def create(path):
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    except FileExistsError:
        return
    with os.fdopen(descriptor, 'wb') as stream:
        stream.write(os.urandom(32))
        stream.flush()
        os.fsync(stream.fileno())
