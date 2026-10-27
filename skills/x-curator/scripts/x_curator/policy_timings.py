"""Timing receipts for one durable allowance, including failed reservations."""


def calls(db, identity, key):
    return [dict(r) for r in db.execute("SELECT id,token,started,finished FROM executions WHERE json_extract(input,?)=? ORDER BY started,id", ('$.' + key, identity))]


def records(db, run, executions):
    tokens = {r['token'] for r in executions} | {run['token']}
    attempts, tools = [], []
    for token in sorted(tokens):
        attempts.append(dict(db.execute('SELECT started,finished,state FROM attempts WHERE token=?', (token,)).fetchone()))
        tools.extend(dict(r) for r in db.execute('SELECT id,name,created AS started,finished FROM quick_tools WHERE token=? ORDER BY created,id', (token,)))
    return attempts, tools


def durations(db, run, attempts):
    finished = [r['finished'] for r in attempts if r['finished'] is not None]
    if len(finished) != len(attempts):
        return dict(processing_seconds=None, capture_to_disposition_seconds=None)
    created = db.execute('SELECT created FROM jobs WHERE account=? AND id=?', (run['account'], run['source'])).fetchone()[0]
    return dict(processing_seconds=max(finished)-run['started'], capture_to_disposition_seconds=max(finished)-created)


def overruns(records, deadline):
    return [r['id'] for r in records if r['finished'] is not None and r['finished'] > deadline]


def measure(db, run, key, search_limit):
    executions = calls(db, run['id'], key)
    attempts, tools = records(db, run, executions)
    violations = overruns(executions + tools, run['deadline'])
    if search_limit is not None and run['searches'] > search_limit:
        violations.append('search allowance')
    return dict(id=run['id'], account=run['account'], source=run['source'], policy='quick' if key == 'check' else 'approved',
                outcome=run['outcome'], searches=run['searches'], search_limit=search_limit, model_calls=len(executions), observed_retries=len(attempts)-1,
                allowance_seconds=run['deadline']-run['started'], **durations(db, run, attempts),
                calls=executions, tools=tools, attempts=attempts, overruns=violations,
                unfinished_receipts=sum(r['finished'] is None for r in executions + tools))
