"""Only intact, revision-matched rejection receipts can inform a new attempt."""
import time

from .claim_validation import nonempty
from .evidence import current_bundle
from .leases import require_lease
from .receipts import digest
from .verdicts import reviewed


def previous_rejection(db, token):
    job = require_lease(db, token, time.time())
    row = db.execute('''SELECT p.id proposal,r.id review,r.token FROM executions r
        JOIN executions p ON p.token=r.token AND p.role='research'
        JOIN attempts a ON a.token=r.token
        WHERE a.account=? AND a.id=? AND r.token!=? AND r.role='review'
          AND r.finished IS NOT NULL ORDER BY r.started DESC LIMIT 1''',
                     (job['account'], job['id'], token)).fetchone()
    if row is None:
        return None
    try:
        return verified_feedback(db, job, row)
    except (ValueError, KeyError, TypeError, OSError):
        return None


def verified_feedback(db, job, row):
    evidence = current_bundle(db, job, row['token'])
    packet, verdict = reviewed(db, row['token'], row['proposal'], row['review'], evidence)
    if not isinstance(verdict, dict):
        raise ValueError('review must be an object')
    findings = verdict.get('findings')
    if not isinstance(findings, list) or not findings:
        raise ValueError('rejection requires concrete findings')
    for finding in findings:
        nonempty(finding)
    if verdict != dict(verdict='reject', proposal_sha=digest(packet), bundle_sha=digest(evidence), findings=findings):
        raise ValueError('rejection does not bind the exact proposal and evidence')
    return {'review': row['review'], 'proposal': packet, 'findings': findings}
