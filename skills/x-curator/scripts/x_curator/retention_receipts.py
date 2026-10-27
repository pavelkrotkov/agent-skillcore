"""Extract retained canonical transcripts one execution at a time, without sorting blobs."""
import json
from .storage import sha256
from .retention_files import table


def unpack(log):
    try:
        value = json.loads(log)
    except (ValueError, UnicodeError):
        return None
    return value if isinstance(value, dict) and value.get('format') in ('x-curator-input-proof-v1', 'x-curator-input-proof-v2') else None


def executions(db, token):
    for row in db.execute('SELECT input_sha,log,log_sha,output,output_sha FROM executions WHERE token=?', (token,)):
        if row[1] and sha256(row[1]) == row[2]:
            yield row[0], unpack(row[1])
        if proof := evidence(row[3], row[4]):
            yield proof['request_sha'], proof


def evidence(output, expected):
    if output and sha256(output.encode()) == expected:
        value = json.loads(output)
        if isinstance(value, dict):
            return value.get('input_proof')
    return None


def receipts(db, token):
    yield from executions(db, token)
    if table(db, 'wiki_runs'):
        row = db.execute('SELECT proposal,review FROM wiki_runs WHERE id=?', (token,)).fetchone()
        for log in filter(None, row or ()):
            if proof := unpack(log):
                yield proof['request_sha'], proof
