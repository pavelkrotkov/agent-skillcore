"""One read-only per-run report joins existing model and tool receipts."""
import json
import sqlite3
from contextlib import closing
from .stage_store import path

from .stage_liveness import interrupted
from .stage_aggregate import summarize
from .stage_receipts import receipt_rows

def index_latency(db, rows):
    generations = [row['context'].get('generation') for row in rows if row['context'].get('generation')]
    if not generations:
        return None
    from .policy_metrics import wiki_index_latency
    try:
        manifest = db.execute('SELECT manifest FROM wiki_builds WHERE id=?', (generations[-1],)).fetchone()
        return wiki_index_latency(db, json.loads(manifest[0])) if manifest else None
    except (sqlite3.OperationalError, TypeError, KeyError, ValueError):
        return None



def prepare_rows(db, run):
    rows = [dict(row) for row in db.execute('SELECT * FROM stage_spans WHERE run=? ORDER BY started,id', (run,))]
    tokens = {json.loads(row['context']).get('attempt') for row in rows}
    tokens.discard(None)
    if tokens:
        markers = ','.join('?' for _ in tokens)
        rows.extend(dict(row) for row in db.execute(
            f"SELECT * FROM stage_spans WHERE run<>? AND json_extract(context,'$.attempt') IN ({markers})",
            (run, *sorted(tokens))))
    for row in rows:
        row['context'] = json.loads(row['context'])
        row['outcome'] = interrupted(row)
    return rows



def report(db, run=None):
    with closing(sqlite3.connect(path(db))) as receipts:
        receipts.row_factory = sqlite3.Row
        if run in (None, 'latest'):
            recent = receipts.execute("SELECT run FROM stage_spans WHERE parent IS NULL AND stage NOT IN ('source.linked_excerpt','source.http_acquisition') ORDER BY rowid DESC LIMIT 1").fetchone()
            run = recent['run'] if recent else None
        rows = prepare_rows(receipts, run)
    if not rows:
        return {'state': 'incomplete', 'run': run, 'reason': 'no historical stage receipts'}
    tokens = sorted({row['context']['attempt'] for row in rows if row['context'].get('attempt')})
    return dict(run=run, **summarize(rows), provider_wait_seconds=None,
                verdict_to_index_seconds=index_latency(db, rows),
                models=receipt_rows(db, tokens, 'executions'),
                tools=receipt_rows(db, tokens, 'quick_tools'))
