"""Finished unresolved runs enter one later review batch without changing old digests."""
import json
import time
from .receipts import digest

from . import deep_permission, deep_store, review_outbox, review_store
from .deep_cli import options


def prepare(db, account, chat, run=None, seconds=600, resource=None, *, native=False):
    options(run, seconds, resource)
    deep_store.initialize(db)
    with db:
        db.execute('BEGIN IMMEDIATE')
        review_store.route(db, account, chat)
        deep_store.recover(db, account, time.time())
        rows = db.execute('''SELECT d.* FROM deep_runs d JOIN research_permissions p ON p.id=d.id
            JOIN jobs j ON j.account=p.account AND j.id=p.source
            WHERE j.state='awaiting_review' AND p.account=? AND d.outcome='inconclusive'
            AND d.id=(SELECT latest.id FROM deep_runs latest JOIN research_permissions lp ON lp.id=latest.id
                WHERE lp.account=p.account AND lp.source=p.source ORDER BY latest.started DESC,latest.id DESC LIMIT 1) AND (d.review_batch IS NULL OR ? IS NOT NULL)
            AND (? IS NULL OR d.id=?) ORDER BY d.started,d.id LIMIT 50''', (account, run, run, run)).fetchall()
        if not rows:
            return None
        key = ['research-review/v1', chat, [r['id'] for r in rows], seconds, resource]
        identity = digest(key + ['native-search'] if native else key)
        existing = db.execute('SELECT id FROM review_deliveries WHERE batch=?', (identity,)).fetchone()
        if existing:
            return review_store.delivery(db, existing[0])
        now = time.time()
        items = [proposal(db, row, identity, seconds, resource, native=native) for row in rows]
        db.execute("INSERT INTO curation_batches VALUES (?,?,'research-review',?,?,'closed')", (identity, account, now, now))
        db.executemany('UPDATE deep_runs SET review_batch=COALESCE(review_batch,?) WHERE id=?', [(identity, row['id']) for row in rows])
        value = dict(id=identity, account=account, kind='research-review', created=now, cutoff=now, state='closed',
                     counts={'pending_decision': len(items)}, items=items, review=items)
        return review_outbox.save(db, value, chat)


def proposal(db, row, batch, seconds, resource, *, native=False):
    _, previous = deep_permission.verified(db, row['id'])
    item = dict(previous, reference=batch + ':' + previous['source'], reason=row['reason'],
                seconds=seconds, previous_run=row['id'], state='pending_decision')
    item.pop('resource', None)
    item.pop('search_mode', None)
    item['scope'] = 'Targeted evidence for the unresolved claim; no full books or videos.'
    if resource is not None:
        item.update(resource=resource, scope='Use only the approved resource and targeted corroboration for this question; preserve partial-reading limitations.')
    if native:
        from .native_search import RESEARCH_MODE
        item['search_mode'] = RESEARCH_MODE
        item['scope'] += ' Codex native search: 12-query target with actual usage recorded; approved deadline remains hard.'
    return item
