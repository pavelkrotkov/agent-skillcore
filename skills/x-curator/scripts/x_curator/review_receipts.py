"""Validate native chat readbacks supplied by the trusted outer chat agent."""
import json

from . import review_store
from .review_native import validate


def observe(db, identity, receipt, message_id):
    review_store.initialize(db)
    with db:
        db.execute('BEGIN IMMEDIATE')
        value = review_store.delivery(db, identity)
        validate(value, receipt, message_id)
        db.execute('UPDATE review_deliveries SET observed=COALESCE(observed,?),failure=NULL WHERE id=?',
                   (json.dumps({'receipt': receipt, 'message': message_id}), identity))
    return {'state': 'delivered', 'delivery': identity}


def failed(db, identity, reason):
    review_store.initialize(db)
    if not reason.strip():
        raise ValueError('delivery failure needs a reason')
    with db:
        review_store.delivery(db, identity)
        db.execute('UPDATE review_deliveries SET failure=? WHERE id=?', (reason, identity))
    return {'state': 'blocked', 'delivery': identity, 'reason': reason}
