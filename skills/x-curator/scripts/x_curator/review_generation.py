"""A later research run makes an older unresolved proposal ineligible for new work."""
from .deep_store import exists
from .receipts import digest
from .quick_store import POLICY
from .quick_replacements import latest as current_check


def require_current(db, account, item):
    original = digest([POLICY, account, item['source'], item['revision']])
    latest = current_check(db, account, item['source'], original)
    if item.get('check', original) != latest:
        raise ValueError('a replacement quick check superseded this request')
    if not exists(db):
        return
    row = db.execute('''SELECT d.id FROM deep_runs d JOIN research_permissions p ON p.id=d.id
        WHERE p.account=? AND p.source=? ORDER BY d.started DESC,d.id DESC LIMIT 1''', (account, item['source'])).fetchone()
    latest = row['id'] if row else None
    if latest != item.get('previous_run'):
        raise ValueError('a newer research attempt superseded this request')
