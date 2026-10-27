"""Delete only named derived artifacts inside a checked private namespace."""
from pathlib import Path
import shutil
import time
from .publication_files import private_target

DAY = 86400


def target(root, relative):
    if Path(relative).is_absolute() or '..' in Path(relative).parts:
        raise ValueError('retention requires a relative private path')
    path = private_target(root, relative)
    # Internal symlinks are refused too: a cleanup namespace must own its files.
    for parent in (path, *path.parents):
        if parent == Path(root):
            break
        if parent.is_symlink():
            raise ValueError('retention refuses symlinked namespaces')
    return path


def old(path, days=7):
    return path.stat().st_mtime < time.time() - days * DAY


def size(path):
    if path.is_dir():
        return sum(p.lstat().st_size for p in path.rglob('*') if not p.is_dir() or p.is_symlink())
    return path.stat().st_size


def remove(root, paths, apply=False):
    paths = [target(root, str(p.relative_to(root))) for p in paths]
    result = dict(files=len(paths), bytes=sum(size(p) for p in paths))
    if apply:
        for path in paths:
            target(root, str(path.relative_to(root)))
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()
    return result


def table(db, name):
    return db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone() is not None
