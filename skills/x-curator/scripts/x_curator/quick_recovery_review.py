"""Replacement outcomes get a new immutable consolidated request, never an old approval."""
import json
import time

from . import batch_report, review_outbox
from .receipts import digest


def prepare(db, batch, chat):
    with db:
        db.execute('BEGIN IMMEDIATE')
        value = batch_report.result(db, batch)
        recovered = db.execute('''SELECT r.replacement FROM quick_recoveries r JOIN curation_members m
            ON m.account=r.account AND m.source=r.source WHERE m.batch=? AND r.review_batch IS NULL''', (batch,)).fetchall()
        if value['state'] != 'closed' or not recovered:
            return None
        return save(db, value, chat, {r['replacement'] for r in recovered})


def save(db, value, chat, checks):
    batch = value['id']
    prior = db.execute('SELECT payload FROM review_deliveries WHERE batch=?', (batch,)).fetchone()
    represented = {i.get('check') for i in json.loads(prior['payload'])['review']} if prior else set()
    identity = digest(['quick-recovery-review/v1', batch, sorted(checks)])
    items = [dict(item, reference=identity + ':' + item['source']) for item in value['review']
             if item.get('check') in checks - represented]
    if not items:
        mark(db, checks, batch)
        return None
    mark(db, checks, identity)
    return deliver(db, value, chat, identity, items)


def deliver(db, value, chat, identity, items):
    now = time.time()
    db.execute("INSERT INTO curation_batches VALUES (?,?,'research-review',?,?,'closed')", (identity, value['account'], now, now))
    value.update(id=identity, kind='research-review', items=items, review=items, counts={'pending_decision': len(items)})
    return review_outbox.save(db, value, chat)


def mark(db, checks, batch):
    db.executemany('UPDATE quick_recoveries SET review_batch=? WHERE replacement=?', ((batch, check) for check in checks))
