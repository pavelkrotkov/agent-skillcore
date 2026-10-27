"""Count observed native queries, including batched searches, from executor events."""
import json

from .model_trace import native


def events(log):
    try:
        return native(log)
    except (ValueError, UnicodeError):
        lines = log.splitlines(keepends=True)
        return [json.loads(line) for line in lines if line.endswith(b'\n') and line.strip()]


def searches(log):
    calls = {}
    for row in events(log):
        item = row.get('item', {})
        if item.get('type') == 'web_search':
            calls[item['id']] = dict(item, finished=row['type'] == 'item.completed')
    return list(calls.values())


def queries(call):
    action = call.get('action', {})
    if action.get('type') != 'search':
        return []
    values = action.get('queries') or [action.get('query')]
    if not isinstance(values, list) or not all(isinstance(q, str) and q.strip() for q in values):
        raise ValueError('native search query usage is incomplete')
    return values


def usage(log):
    calls = searches(log)
    return dict(queries=[q for call in calls for q in queries(call)],
                unfinished=[call['id'] for call in calls if not call['finished']])


def urls(log):
    return {result['url'] for call in searches(log) if call['finished'] and queries(call)
            for result in call.get('results', []) if result.get('url')}
