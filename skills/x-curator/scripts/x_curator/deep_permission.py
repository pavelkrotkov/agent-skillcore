"""Reconstruct the exact permission from its immutable proposal and human reply."""
import json

from . import review_native, review_reply, review_store
from .receipts import digest


def verified(db, identity):
    row = db.execute('SELECT * FROM research_permissions WHERE id=?', (identity,)).fetchone()
    if row is None:
        raise ValueError('explicit item-specific research permission required')
    value = dict(row)
    require_current(db, value)
    delivery = review_store.delivery(db, value['delivery'])
    review_native.require_observed(delivery)
    proposal, = [p for p in json.loads(delivery['payload'])['review'] if p['reference'] == value['reference']]
    expected = dict(proposal, account=json.loads(delivery['payload'])['account'])
    if any(value[key] != expected[key] for key in ('account', 'source', 'revision', 'question', 'scope', 'seconds')):
        raise ValueError('permission differs from the observed request')
    if value['id'] != digest([value['delivery'], value['reference']]):
        raise ValueError('permission identity changed')
    human(db, value, delivery)
    return value, proposal


def human(db, value, delivery):
    decision = db.execute('SELECT * FROM review_decisions WHERE delivery=? AND reference=?',
                          (value['delivery'], value['reference'])).fetchone()
    reply = db.execute('SELECT * FROM review_replies WHERE chat=? AND message=?',
                       (delivery['chat'], decision['reply'])).fetchone()
    message = review_native.message(json.loads(reply['readback']), delivery['chat'], decision['reply'], 'userMessage')
    proposals = {p['reference'] for p in json.loads(delivery['payload'])['review']}
    actions = review_reply.parse(review_reply.human_text(message), value['delivery'], proposals)
    if decision['action'] != 'research' or actions.get(value['reference']) != 'research':
        raise ValueError('the human did not approve this research')


def require_current(db, value):
    if value['consumed'] is None and db.execute('SELECT 1 FROM research_supersessions WHERE previous=?', (value['id'],)).fetchone():
        raise ValueError('research permission superseded by a fresh human approval')
