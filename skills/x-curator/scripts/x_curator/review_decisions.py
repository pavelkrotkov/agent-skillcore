"""Apply an observed direct human reply atomically without scheduling any research."""
import json

from . import review_native, review_reply, review_store
from .review_permissions import decide


def apply(db, identity, receipt, human_message, *, human_origin_confirmed=False):
    if human_origin_confirmed is not True:
        raise ValueError('native caller must confirm this message came directly from the human')
    review_store.initialize(db)
    with db:
        db.execute('BEGIN IMMEDIATE')
        value = review_store.delivery(db, identity)
        review_native.require_observed(value)
        message = review_native.message(receipt, value['chat'], human_message, 'userMessage')
        proposals = {i['reference']: i for i in json.loads(value['payload'])['review']}
        actions = review_reply.parse(review_reply.human_text(message), identity, proposals)
        encoded = json.dumps(message, sort_keys=True)
        if replayed(db, value, human_message, encoded):
            return {'state': 'recorded', 'delivery': identity, 'decisions': actions}
        for reference, action in actions.items():
            decide(db, value, proposals[reference], action, human_message)
        db.execute('INSERT OR IGNORE INTO review_replies VALUES (?,?,?,?,?)',
                   (value['chat'], human_message, identity, encoded, json.dumps(receipt)))
    return {'state': 'recorded', 'delivery': identity, 'decisions': actions}



def replayed(db, value, human_message, encoded):
    prior = db.execute('SELECT delivery,receipt FROM review_replies WHERE chat=? AND message=?',
                       (value['chat'], human_message)).fetchone()
    if prior and (prior['delivery'] != value['id'] or prior['receipt'] != encoded):
        raise ValueError('conflicting replay of a human reply')
    return prior is not None
