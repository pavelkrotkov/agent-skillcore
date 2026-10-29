"""Retain original execution hashes, session identities and hashes of event copies."""
from .model_events import result
from .storage import sha256

def publication(db, identity):
    from .compact_targets import token
    return attempt(db, token(db, identity))


def attempt(db, current):
    rows = db.execute('''SELECT id,role,model,input_sha,output_sha,log_sha,session,started,finished
        FROM executions WHERE token=? ORDER BY started,id''', (current,))
    executions = [dict(row) for row in rows]
    sessions, events = copies(db, current)
    sessions.update(row['session'] for row in executions if row['session'] and row['finished'] is not None)
    return dict(executions=executions, sessions=sorted(sessions), events=events)


def mapping(row):
    logs = {name: dict(sha256=sha256(row[name]), session=result(row[name])[0]) for name in ('proposal', 'review')}
    return dict(logs=logs, sessions=sorted({p['session'] for p in logs.values()}))


def copies(db, token):
    from .retention_receipts import receipts
    from .retention_copies import session_ids
    sessions, events = set(), {}
    finished = {r[0] for r in db.execute('SELECT input_sha FROM executions WHERE token=? AND finished IS NOT NULL', (token,))}
    for identity, proof in receipts(db, token):
        if proof and identity in finished:
            sessions.update(session_ids(proof))
            events['runs/' + token + '/' + identity + '.jsonl'] = sha256(proof['events'].encode())
    return sessions, events
