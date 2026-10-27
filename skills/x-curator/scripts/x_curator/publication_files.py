"""Atomic immutable writes permit replay after any process interruption."""
import os
from pathlib import Path
import tempfile


def private_target(root, relative):
    root = Path(root).resolve()
    target = root / relative
    if root not in target.resolve().parents or any((p / ".git").exists() for p in target.resolve().parents):
        raise ValueError("publication must stay in private state outside Git")
    if target.is_symlink():
        raise ValueError("publication must not be a symlink")
    return target


def write_verified(root, relative, body):
    target = private_target(root, relative)
    target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with tempfile.NamedTemporaryFile(dir=target.parent) as temporary:
        temporary.write(body)
        temporary.flush()
        os.fsync(temporary.fileno())
        try:
            os.link(temporary.name, target)
        except FileExistsError:
            pass
    if target.read_bytes() != body:
        raise ValueError("immutable publication conflict")
    directory = os.open(target.parent, os.O_RDONLY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)
