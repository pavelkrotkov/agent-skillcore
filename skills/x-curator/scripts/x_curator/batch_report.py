"""One readable result per batch; pending approval is a completed quick disposition."""
from collections import Counter
import json

from . import batch_items, batch_store, daily_plan, quick_failures


def result(db, identity):
    batch = db.execute('SELECT * FROM curation_batches WHERE id=?', (identity,)).fetchone()
    if batch is None:
        raise ValueError('unknown curation batch')
    if batch['kind'] == 'research-review':
        payload = db.execute('SELECT payload FROM review_deliveries WHERE batch=?', (identity,)).fetchone()
        return json.loads(payload[0])
    rows = db.execute('''SELECT j.*,m.batch,q.id check_id,q.token check_token,q.outcome,q.reason,q.revision,q.searches,q.execution,e.output
        FROM curation_members m JOIN jobs j ON j.account=m.account AND j.id=m.source
        LEFT JOIN quick_checks q ON q.id=(SELECT id FROM quick_checks
            WHERE account=m.account AND source=m.source ORDER BY started DESC,id LIMIT 1)
        LEFT JOIN executions e ON e.id=q.execution WHERE m.batch=? ORDER BY j.created,j.id''', (identity,))
    items = [batch_items.item(db, row, quick_failures.retrieval(db, row['check_token'])) for row in rows]
    counts = dict(Counter(item['state'] for item in items))
    return dict(batch, **daily_plan.metadata(db, batch), counts=counts, items=items, review=[i for i in items if i['state'] == 'pending_decision'])


def report(db, identity=None):
    batch_store.initialize(db)
    with db:
        db.execute('BEGIN IMMEDIATE')
        for row in db.execute('SELECT DISTINCT account FROM curation_batches').fetchall():
            batch_store.close_finished(db, row['account'])
        ids = [identity] if identity else [r[0] for r in db.execute('SELECT id FROM curation_batches ORDER BY created,id')]
        return {'state': 'checkpoint', 'batches': [result(db, batch) for batch in ids]}
