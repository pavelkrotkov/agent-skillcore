"""Replay the original verifier before recording an irreversible history replacement."""
from . import compact_dependencies, compact_provenance
from .read_set import ReadSet


def capture(db, root, identity):
    reads = ReadSet(db)
    if identity[0] == 'publication':
        value = approved_source(reads, db, root, identity[1])
        provenance = compact_provenance.publication(db, identity[1])
    else:
        from .wiki_mapping_receipts import verified
        row = reads.execute('SELECT * FROM wiki_runs WHERE id=?', (identity[1],)).fetchone()
        value = verified(row)[1]
        provenance = compact_provenance.mapping(row)
    return compact_dependencies.stage(reads, value, identity[0], provenance)


def approved_source(reads, db, root, identity):
    from .evidence import current_bundle
    from .verdicts import model_approval
    from .compact_validation import publication as verify_current
    row = reads.execute('SELECT * FROM publications WHERE id=?', (identity,)).fetchone()
    token = reads.execute('SELECT token FROM executions WHERE id=?', (row['proposal'],)).fetchone()[0]
    job = db.execute('SELECT * FROM jobs WHERE account=? AND id=?', (row['account'], row['source'])).fetchone()
    evidence = current_bundle(db, job, token)
    value = model_approval(reads, token, row['proposal'], row['review'], evidence)
    verify_current(db, root, identity, value)
    return value


def clear_transient_decoders():
    from . import model_trace
    model_trace.decoded.cache_clear()
    model_trace.verified_native.cache_clear()
