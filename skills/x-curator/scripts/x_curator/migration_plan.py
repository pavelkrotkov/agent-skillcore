"""Reconcile captured identities without modifying their live corpus or files."""
from collections import Counter

from . import native_search
from .receipts import digest
from .migration_inventory import item, POLICY


def captures(db):
    rows = db.execute('''SELECT c.account,s.id,min(r.fetched) AS created,
        json_group_array(json_array(s.entry,r.sha256)) AS revisions FROM selections s
        JOIN collections c ON c.id=s.run JOIN responses r ON r.run=s.run AND r.number=s.response
        GROUP BY c.account,s.id ORDER BY c.account,s.id''')
    return [dict(row) for row in rows]


def build(db, root, proof_db=None):
    items = [item(db, root, row, proof_db or db) for row in captures(db)]
    orphaned = orphans(db, items)
    blockers = [r['source'] for r in items if r['disposition'] == 'blocked']
    blockers.extend(orphaned)
    plan = dict(policy=POLICY, search_mode=native_search.MODE, historical_complete=False, items=items, blockers=blockers,
                counts=dict(Counter(r['disposition'] for r in items)), captured=len(items))
    return dict(plan, state='blocked' if blockers else 'checkpoint', digest=digest(plan), applied=False)


def orphans(db, items):
    captured = {(r['account'], r['source']) for r in items}
    return [dict(r) for r in db.execute('SELECT account,id FROM jobs') if (r['account'], r['id']) not in captured]
