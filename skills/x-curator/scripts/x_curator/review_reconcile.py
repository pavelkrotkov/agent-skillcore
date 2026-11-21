"""Reconcile closed batch outboxes even when a cycle processes no new sources."""
from . import batch_store, review_outbox, review_store, quick_recovery_review


def flush(db, account):
    review_store.initialize(db)
    with db:
        route = db.execute('SELECT chat FROM review_routes WHERE account=?', (account,)).fetchone()
        batch_store.close_finished(db, account)
        batches = db.execute('''SELECT id FROM curation_batches b WHERE account=? AND state='closed'
            AND kind IN ('backlog','daily') AND EXISTS (
                SELECT 1 FROM curation_members m JOIN jobs j ON j.account=m.account AND j.id=m.source
                WHERE m.batch=b.id AND j.state IN ('awaiting_review','needs_action')) AND NOT EXISTS (
                SELECT 1 FROM review_deliveries d WHERE d.batch=b.id) ORDER BY created,id''', (account,)).fetchall()
    if route is None:
        return []
    results = [prepare(db, row['id'], route['chat']) for row in batches]
    for row in db.execute("""SELECT DISTINCT b.id FROM curation_batches b JOIN curation_members m ON m.batch=b.id
        JOIN quick_recoveries r ON r.account=m.account AND r.source=m.source
        WHERE b.account=? AND b.state='closed' AND b.kind IN ('backlog','daily') AND r.review_batch IS NULL""", (account,)).fetchall():
        value = quick_recovery_review.prepare(db, row['id'], route['chat'])
        if value:
            results.append({'batch': value['batch'], 'delivery': value['id']})
    return results


def prepare(db, batch, chat):
    try:
        value = review_outbox.prepare(db, batch, chat)
        return {'batch': batch, 'delivery': value['id'] if value else None}
    except ValueError as exc:
        return {'batch': batch, 'state': 'blocked', 'reason': str(exc)}
