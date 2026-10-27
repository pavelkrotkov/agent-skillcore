"""Bind human decisions to the checked source; deferral can be revisited explicitly."""
import json
import time

from .receipts import digest
from .quick_failures import for_source
from .revisions import revision
from .source_evidence import selected_source


def decide(db, delivery, item, action, message):
    key = (delivery['id'], item['reference'])
    previous = db.execute('SELECT action FROM review_decisions WHERE delivery=? AND reference=?', key).fetchone()
    if previous:
        if previous['action'] == action:
            return
        if previous['action'] != 'defer':
            raise ValueError('item already decided; changing permission requires a new explicit request')
    account = json.loads(delivery['payload'])['account']
    require_pending(db, account, item, action)
    db.execute('''INSERT INTO review_decisions VALUES (?,?,?,?,?) ON CONFLICT(delivery,reference)
        DO UPDATE SET action=excluded.action,reply=excluded.reply,created=excluded.created''', (*key, action, message, time.time()))
    if action == 'research':
        db.execute('INSERT INTO research_permissions VALUES (?,?,?,?,?,?,?,?,?,NULL)',
                   (digest(key), *key, account, item['source'], item['revision'], item['question'], item['scope'], item['seconds']))
        supersede(db, account, item['source'], digest(key))
    if action == 'exclude':
        db.execute("UPDATE jobs SET state='excluded',action='Excluded by explicit human decision' WHERE account=? AND id=?",
                   (account, item['source']))


def require_pending(db, account, item, action):
    from .review_generation import require_current
    require_current(db, account, item)
    if action == 'research' and not item.get('previous_run') and for_source(db, account, item['source']):
        raise ValueError('retrieval failure requires operator triage before a new research decision')
    job = dict(db.execute('SELECT * FROM jobs WHERE account=? AND id=?', (account, item['source'])).fetchone())
    if job['state'] != 'awaiting_review' or digest(revision(selected_source(db, job)['entry'])) != item['revision']:
        raise ValueError('source changed or no longer awaits a decision; prepare a fresh request')


def supersede(db, account, source, replacement):
    db.execute('''INSERT INTO research_supersessions(previous,replacement)
        SELECT p.id,? FROM research_permissions p
        WHERE p.account=? AND p.source=? AND p.id<>? AND p.consumed IS NULL
        AND NOT EXISTS(SELECT 1 FROM research_supersessions s WHERE s.previous=p.id)''',
        (replacement, account, source, replacement))
