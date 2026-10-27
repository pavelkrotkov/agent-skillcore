"""Create only checked private document parents and sync changed directories once."""
from contextlib import suppress
import os
from pathlib import Path
from .proof_namespace import private_root,directory


def destination(root,relative,namespace,folders):
    parts=Path(relative).parts
    if not parts or os.path.isabs(relative) or {'.git','..'}.intersection(parts):
        raise ValueError('wiki document escaped private generation')
    parent=private_root(root,namespace)
    for part in parts[:-1]:
        parent=os.path.join(parent,part)
        if parent not in namespace:
            with suppress(FileExistsError):
                os.mkdir(parent,0o700)
            directory(parent,namespace)
            folders.update((parent,os.path.dirname(parent)))
    return Path(os.path.join(parent,parts[-1]))


def sync(folder):
    handle=os.open(folder,os.O_RDONLY)
    try:
        os.fsync(handle)
    finally:
        os.close(handle)
