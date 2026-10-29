"""Keep approval dependencies and original evidence hashes, without transcript bodies."""
from marshal import dumps

from .audit_seal import policy
from .read_set import ReadSet, ChangedDependencies
from .row_fingerprint import query_stamp, row_digest


def stage(reads, value, kind, provenance):
    stamps, files = reads.fingerprint()
    return dict(version=1, verifier=policy(kind), provenance=provenance, value=dumps(value),
                queries=stamps,
                files=files, metadata=reads.metadata, pending=True)


def stamp(db, query, pending):
    return query_stamp(db, query) if pending else row_digest(db.execute(*query))


def verify(db, record):
    for query, expected in record['queries'].items():
        if stamp(db, query, record['pending']) != expected:
            raise ChangedDependencies('compact approval dependency changed')
    reads = ReadSet(db)
    reads.files, reads.metadata = dict(record['files']), dict(record['metadata'])
    reads.verify(({}, record['files']))


def activate(db, record):
    result = dict(record, pending=False)
    result['queries'] = {q: stamp(db, q, False) for q in record['queries']}
    return result
