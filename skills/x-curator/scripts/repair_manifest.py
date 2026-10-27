"""Frozen private inputs and recovery receipts for a bounded qualification."""
import json

from x_curator import native_search
from x_curator.receipts import digest

SCOPE = dict(seconds_per_item=120, search_target=3, search_mode=native_search.MODE,
             extra_requests_per_item=20, extra_attempts_per_item=1,
             deep_research=False, worker_timers_enabled=False)
CATEGORIES = {'oversized_html', 'draft_body_support', 'irrelevant_search', 'deadline_with_html_failure'}


def identity(manifest):
    items, scope = manifest['items'], manifest['scope']
    keys = [(item['account'], item['source']) for item in items]
    expected = dict(SCOPE, count=len(items))
    if not 1 <= len(items) <= 10 or len(set(keys)) != len(items) or scope != expected:
        raise ValueError('qualification requires unique items and the fixed bounded scope')
    if any(item['category'] not in CATEGORIES for item in items):
        raise ValueError('unknown qualification failure class')
    return digest(['repair-qualification/v1', manifest['repair_release'], scope, items])


def receipt(db, item, approval):
    row = db.execute('SELECT * FROM quick_recoveries WHERE original=?', (item['original'],)).fetchone()
    if row is None:
        return None
    evidence = json.loads(row['evidence'])
    expected = digest(['retrieval-repair/v1', item['original']])
    if (row['replacement'], row['account'], row['source'], evidence.get('approval'), evidence.get('item')) != (
            expected, item['account'], item['source'], approval, item):
        raise ValueError('qualification recovery receipt differs from this manifest')
    return evidence
