"""Dynamic evidence must appear in the native model transcript unchanged."""
import json
from itertools import takewhile

from .model_trace import envelope, records


def dynamic(db, token, log, seen, started=0, finished=float('inf')):
    proof = envelope(log)
    if proof is None:
        raise ValueError('quick checks require a full native execution proof')
    outputs = [r['payload'].get('output') for r in filter(tool_output, takewhile(before_final, records(proof['rollout'].encode())))]
    for row in db.execute("SELECT * FROM quick_tools WHERE token=? AND output IS NOT NULL AND created>=? AND created<? AND finished<=? ORDER BY created,id", (token, started, finished, finished)):
        output = json.loads(row['output'])
        content, *_ = output['content']
        text = content['text']
        if not observed(outputs, output['content']):
            raise ValueError('controller tool response absent from original model rollout')
        if (row['name'], output['isError']) == ('read', False):
            value = json.loads(text)
            seen[value['capture']] = value['evidence']


def contains(value, text):
    if isinstance(value, str):
        if value == text:
            return True
        try:
            value = json.loads(value)
        except ValueError:
            # LF framing preserves Unicode separators inside JSON string values.
            return '\n' in value and nested(value.split('\n'), text)
    return nested(value, text)


def tool_output(row):
    return (row['type'], row.get('payload', {}).get('type')) in (
        ('response_item', 'function_call_output'), ('response_item', 'custom_tool_call_output'))


def nested(value, text):
    if isinstance(value, dict):
        value = list(value.values())
    return isinstance(value, list) and any(contains(item, text) for item in value)


def before_final(row):
    payload = row.get('payload', {})
    return (payload.get('type'), payload.get('role'), payload.get('phase')) != ('message', 'assistant', 'final_answer')


def observed(outputs, content):
    return all(any(contains(value, item['text']) for value in outputs) for item in content)
