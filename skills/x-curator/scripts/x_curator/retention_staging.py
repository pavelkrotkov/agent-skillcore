"""Remove aged, byte-identical staging copies only after a run has finished."""
import filecmp
import re
import time
from .retention_files import DAY, target, old, remove, table
from .retention_receipts import receipts
from .retention_copies import copies, native_index


def finished(db):
    tokens = set()
    if table(db, 'attempts'):
        tokens.update(row[0] for row in db.execute("SELECT token FROM attempts WHERE finished<? AND state!='leased'", (time.time() - 7 * DAY,)))
        tokens.difference_update(row[0] for row in db.execute("SELECT token FROM jobs WHERE state='leased' AND token IS NOT NULL"))
    if table(db, 'wiki_runs'):
        tokens.update(row[0] for row in db.execute("SELECT id FROM wiki_runs WHERE state IN ('accepted','failed','interrupted') AND expires<?", (time.time() - 7 * DAY,)))
    return tokens


def images(root, folder):
    for path in folder.iterdir():
        if re.fullmatch(r'[0-9a-f]{64}\.(png|jpg|gif|webp)', path.name) and not path.is_symlink() and old(path):
            original = target(root, 'blobs/' + path.stem)
            if original.is_file() and filecmp.cmp(path, original, shallow=False):
                yield path


def run(db, root, apply=False):
    native_index.cache_clear()
    paths = set()
    for token in finished(db):
        folder = target(root, 'runs/' + token)
        if not folder.is_dir():
            continue
        paths.update(images(root, folder))
        for identity, proof in receipts(db, token):
            paths.update(copies(root, folder, identity, proof))
    return remove(root, sorted(paths), apply)
