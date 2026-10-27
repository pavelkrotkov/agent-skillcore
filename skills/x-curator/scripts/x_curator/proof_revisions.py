"""Transactional row revisions make unchanged proof dependencies cheap to fence."""
import re
from .proof_revision_sql import initialize, initialize_table
from .proof_query import projection

from .proof_revision_state import state,remember


def prepare(db):
    with db:
        actual=initialize(db)
        tables=tuple(source_tables(db))
        for table in tables:
            initialize_table(db,table,actual)
    remember(db,tables)


def stamp(db,query):
    from .row_fingerprint import row_digest
    tracked=state(db)
    sql=projection(query[0],tracked[1]) if tracked else None
    value=row_digest(db.execute(sql or query[0],query[1]))
    return row_digest(((tracked[0],value),)) if sql else value


def epoch(db):
    tracked=state(db)
    return tuple(db.execute('SELECT coalesce(sum(version),0),count(*) FROM proof_rows').fetchone()) if tracked and tracked[2] else None


def source_tables(db):
    for row in db.execute('PRAGMA table_list'):
        if eligible(row) and not shadowed(db,row[1]):
            yield row[1]


def eligible(row):
    return row[0]=='main' and row[2]=='table' and not row[4] and re.fullmatch(r'(?!sqlite_|proof_)\w+',row[1])


def shadowed(db,table):
    return any(row[1].lower() in ('rowid','_rowid_','oid') for row in db.execute(f'PRAGMA table_info("{table}")'))
