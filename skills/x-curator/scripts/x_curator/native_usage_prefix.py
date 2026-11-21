"""Count only trustworthy native query events before malformed bytes."""
import json

from .native_search_trace import queries


def count(log):
    calls = {}
    for line in log.splitlines():
        if not line.strip():
            continue
        try:
            remember(calls, json.loads(line))
        except (ValueError, UnicodeError, KeyError, TypeError):
            break
    return sum(len(value) for value in calls.values())


def remember(calls, row):
    if not isinstance(row, dict) or not isinstance(row.get('type'), str):
        raise ValueError('native event shape is incomplete')
    item = row.get('item', {})
    if not isinstance(item, dict):
        raise ValueError('native item shape is incomplete')
    if item.get('type') == 'web_search':
        observed = queries(item)
        if observed:
            calls[item['id']] = observed
