"""Remove closed model-history copies only for authenticated completed approvals."""

from . import compact_seal
from .compact_history_files import candidates


def known(db, root):
    sessions, events = set(), {}
    rows = db.execute('SELECT kind,identity FROM compact_approvals WHERE active=1').fetchall()
    for row in rows:
        proof = compact_seal.read(db, root, tuple(row))['provenance']
        sessions.update(proof.get('sessions', ()))
        events.update(proof.get('events', {}))
    return sessions, events


def run(db, root):
    paths = candidates(root, *known(db, root))
    allocated = sum(p.stat().st_blocks * 512 for p in paths)
    for path in paths:
        path.unlink()
    return dict(files=len(paths), allocated_bytes=allocated)
