"""Evidence-phase outputs contain native histories too; keep only bound receipt facts."""
import json

from .receipts import digest, encoded
from .storage import sha256
from .retention_copies import session_ids


def summary(output):
    value = json.loads(output)
    proof = value['input_proof']
    compact = dict(format='compact-input-proof/v1', original_format=proof['format'],
                   request_sha=proof['request_sha'], prompt_sha=proof['prompt_sha'],
                   images=proof['images'], sessions=session_ids(proof),
                   original_proof_sha=digest(proof), profile_sha=digest(proof['profile']),
                   events_sha=sha256(proof['events'].encode()), rollout_sha=sha256(proof['rollout'].encode()))
    return encoded(dict(value, input_proof=compact)).decode()


def rows(db, token):
    return db.execute('''SELECT id,output FROM executions WHERE token=? AND finished IS NOT NULL
        AND role='factcheck_evidence' AND output IS NOT NULL''', (token,)).fetchall()


def savings(db, token):
    return sum(len(row['output'].encode()) - len(summary(row['output']).encode()) for row in rows(db, token))


def purge(db, token):
    for row in rows(db, token):
        db.execute('UPDATE executions SET output=? WHERE id=?', (summary(row['output']), row['id']))
