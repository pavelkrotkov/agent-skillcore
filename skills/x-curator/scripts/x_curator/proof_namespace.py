"""Check private parent namespaces once per synchronous verification fence."""
import os
from pathlib import Path
import stat


def target(file,cache):
    root,relative=file
    base=private_root(root,cache)
    relative=str(relative)
    parts=relative.split(os.sep)
    if not relative or os.path.isabs(relative) or '..' in parts:
        raise ValueError('proof file escaped private state')
    parent=base
    for part in parts[:-1]:
        parent=os.path.join(parent,part)
        directory(str(parent),cache)
    return os.path.join(parent,parts[-1])


def directory(path,cache):
    if path not in cache:
        if not stat.S_ISDIR(os.stat(path,follow_symlinks=False).st_mode) or os.path.exists(os.path.join(path,'.git')):
            raise ValueError('proof namespace contains a symlink or Git checkout')
        cache[path]=True


def private_root(root,cache):
    key=('root',str(root))
    if key not in cache:
        base=Path(root).resolve()
        for parent in (base,*base.parents):
            directory(str(parent),cache)
        cache[key]=str(base)
    return cache[key]

def identity(info):
    if not stat.S_ISREG(info.st_mode):
        raise ValueError('proof file must be a regular private file')
    return info.st_dev,info.st_ino,info.st_mode,info.st_nlink,info.st_size,info.st_mtime_ns,info.st_ctime_ns
