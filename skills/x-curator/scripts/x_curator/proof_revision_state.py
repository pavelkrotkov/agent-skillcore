"""Adopt existing transactional revisions read-only, including inside audit snapshots."""
from .proof_revision_sql import GUARDS,changes,require

_SCHEMAS={}


def remember(db,tables):
    value=db.execute('PRAGMA schema_version').fetchone()[0],frozenset(tables),complete(db,tables)
    _SCHEMAS[db]=value
    if len(_SCHEMAS)>128:
        del _SCHEMAS[next(iter(_SCHEMAS))]
    return value


def state(db):
    version=db.execute('PRAGMA schema_version').fetchone()[0]
    if (previous:=_SCHEMAS.get(db)) and previous[0]==version:
        return previous
    present=db.execute("SELECT count(*) FROM sqlite_master WHERE name IN ('proof_rows','proof_tables')").fetchone()[0]
    if not present:
        return None
    if present!=2:
        raise ValueError('proof revision infrastructure is incomplete')
    actual=dict(db.execute("SELECT name,sql FROM sqlite_master WHERE type='trigger'"))
    require(GUARDS,actual)
    tables={r[0] for r in db.execute('SELECT name FROM proof_tables')}
    for table in tables:
        require(dict(changes(table)),actual)
    return remember(db,tables)


def complete(db,tables):
    rows=db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT GLOB 'sqlite_*' AND name NOT IN ('proof_rows','proof_tables')")
    return {row[0] for row in rows}<=set(tables)
