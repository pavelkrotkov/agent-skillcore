"""Freeze one status/approval digest per completed batch; retries return the same request."""
import json
import time

from . import batch_report, batch_store, review_render, review_store
from .receipts import digest

render = review_render.legacy
status_render = review_render.current


def prepare(db, batch, chat):
    review_store.initialize(db)
    with db:
        db.execute('BEGIN IMMEDIATE')
        value = batch_report.result(db, batch)
        review_store.route(db, value['account'], chat)
        existing = db.execute('SELECT id FROM review_deliveries WHERE batch=?', (batch,)).fetchone()
        if existing:
            return review_store.delivery(db, existing[0])
        batch_store.close_finished(db, value['account'])
        value = batch_report.result(db, batch)
        if value['state'] != 'closed':
            raise ValueError('batch processing is not finished')
        if not value['review'] and not review_render.failures(value):
            return None
        return save(db, value, chat)


def save(db, value, chat):
    identity = digest(['chat-review/v2', value['id'], chat, value])
    text = status_render(identity, value)
    db.execute('INSERT INTO review_deliveries(id,batch,chat,payload,message,created) VALUES(?,?,?,?,?,?)',
               (identity, value['id'], chat, json.dumps(value), text, time.time()))
    return review_store.delivery(db, identity)


def status(db):
    review_store.initialize(db)
    return {'state': 'checkpoint', 'deliveries': [dict(row) for row in db.execute('''
        SELECT id,batch,chat,created,observed IS NOT NULL AS delivered,failure,
        (SELECT count(*) FROM review_decisions WHERE delivery=d.id) AS decisions
        FROM review_deliveries d ORDER BY created,id''')]}
