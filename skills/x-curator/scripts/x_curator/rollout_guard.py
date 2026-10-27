"""A completed response is insufficient when the original evidence was compacted."""
from .model_trace import records
from .rollout_messages import verify_input as verify_messages_input, verify_answer


def verify(proof):
    from .model_events import result
    _, packet = result(proof['events'].encode())
    verify_answer(verify_input(proof), packet)


def verify_input(proof):
    events = records(proof['events'].encode())
    rows = records(proof['rollout'].encode())
    verify_session(events, rows)
    if any(changed_context(row) for row in rows):
        raise ValueError('model context was compacted or truncated')
    messages = messages_in(rows)
    verify_messages_input(messages, proof)
    return messages


def changed_context(row):
    kinds = (row['type'], row.get('payload', {}).get('type', ''))
    return any(word in kind.lower() for kind in kinds for word in ('compact', 'truncat'))


def messages_in(rows):
    return [r["payload"] for r in rows if r["type"] == "response_item" and r["payload"].get("type") == "message"]


def verify_session(events, rows):
    expected = [e['thread_id'] for e in events if e['type'] == 'thread.started']
    sessions = [r['payload']['id'] for r in rows if r['type'] == 'session_meta']
    if len(expected) != 1 or sessions != expected:
        raise ValueError('rollout session does not match executor session')
