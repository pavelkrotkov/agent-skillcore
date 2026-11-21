"""Select only exact retained controller failures with unchanged source revisions."""
from . import quick_retry
from .receipts import digest
from .revisions import revision
from .source_evidence import selected_source

LEGACY = ('Quick check inconclusive: DeadlineExceeded:', 'Quick check inconclusive: OSError:',
          'Quick check inconclusive: TimeoutError:', 'Quick check inconclusive: WorkerFailure:',
          'Quick check inconclusive: OperationalError: database is locked')


def candidates(db, account, sources=()):
    rows = db.execute('''SELECT j.*,a.token last_token,a.action last_action,a.finished,
        q.id check_id,q.revision,q.outcome,q.reason,q.execution FROM jobs j JOIN attempts a ON a.token=(
            SELECT token FROM attempts WHERE account=j.account AND id=j.id ORDER BY started DESC,token DESC LIMIT 1)
        LEFT JOIN quick_checks q ON q.token=a.token
        WHERE j.account=? AND j.state IN ('awaiting_review','needs_action') AND j.attempts<j.max_attempts
        AND NOT EXISTS (SELECT 1 FROM quick_retry_failures f WHERE f.token=a.token)
        AND NOT EXISTS (SELECT 1 FROM research_permissions p WHERE p.account=j.account AND p.source=j.id)
        AND NOT EXISTS (SELECT 1 FROM review_decisions d JOIN review_deliveries v ON v.id=d.delivery
            WHERE json_extract(v.payload,'$.account')=j.account AND substr(d.reference,instr(d.reference,':')+1)=j.id)
        ORDER BY j.id''', (account,)).fetchall()
    selected = [row for row in rows if row['id'] in sources] if sources else rows
    return list(filter(None, (candidate(db, dict(row)) for row in selected)))


def candidate(db, row):
    if not (row['last_action'] or '').startswith(LEGACY):
        return None
    if not controller_failure(row):
        return None
    current = digest(revision(selected_source(db, row)['entry']))
    if row['revision'] and row['revision'] != current:
        return None
    return dict(account=row['account'], source=row['id'], revision=current, token=row['last_token'],
                check=row['check_id'], attempts=row['attempts'], max_attempts=row['max_attempts'],
                reason=row['last_action'], next_at=max(row['next_at'], (row['finished'] or 0) + quick_retry.delay(row['attempts'])))


def controller_failure(row):
    if not row['check_id']:
        return True
    return not row['execution'] and row['outcome'] == 'inconclusive' and row['reason'] == row['last_action']
