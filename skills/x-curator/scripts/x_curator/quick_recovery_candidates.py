"""Select unchanged, undecided items with retained evidence of repaired tool defects."""
import json

from .receipts import digest
from .revisions import revision
from .source_evidence import selected_source


ERRORS = {'substring not found',
          'registered source and bounded literal match required'}


def defects(db, check):
    found = []
    for row in db.execute('SELECT * FROM quick_tools WHERE token=? ORDER BY created,id', (check['token'],)):
        output = json.loads(row['output'] or '{}')
        if output.get('isError') and repaired(db, check, row['name'], output['content'][0]['text']):
            found.append(dict(id=row['id'], sha=digest(dict(row))))
    return found


def repaired(db, check, name, error):
    if error == 'search engine URLs cannot be read as sources':
        return name == 'search'
    if error in ERRORS:
        return True
    return error == 'quick source unavailable; redirects are not followed' and db.execute(
        'SELECT 1 FROM retrievals WHERE token=? AND status IN (301,302,303,307,308) LIMIT 1', (check['token'],)).fetchone() is not None


def candidates(db):
    rows = db.execute('''SELECT q.*,j.attempts,j.max_attempts FROM quick_checks q
        JOIN jobs j ON j.account=q.account AND j.id=q.source
        WHERE j.state='awaiting_review' AND q.outcome='inconclusive'
        AND q.id=(SELECT id FROM quick_checks WHERE account=q.account AND source=q.source ORDER BY started DESC,id DESC LIMIT 1)
        AND NOT EXISTS (SELECT 1 FROM quick_recoveries r WHERE r.account=q.account AND r.source=q.source)
        AND NOT EXISTS (SELECT 1 FROM research_permissions p WHERE p.account=q.account AND p.source=q.source)
        AND NOT EXISTS (SELECT 1 FROM review_decisions d JOIN review_deliveries v ON v.id=d.delivery
            WHERE json_extract(v.payload,'$.account')=q.account AND substr(d.reference,instr(d.reference,':')+1)=q.source)
        ORDER BY q.account,q.source''').fetchall()
    return [item for row in rows if (item := candidate(db, dict(row))) is not None]


def candidate(db, check):
    job = dict(db.execute('SELECT * FROM jobs WHERE account=? AND id=?', (check['account'], check['source'])).fetchone())
    if digest(revision(selected_source(db, job)['entry'])) != check['revision']:
        return None
    evidence = defects(db, check)
    if not evidence:
        return None
    return dict(original=check['id'], replacement=digest(['retrieval-repair/v1', check['id']]),
                account=check['account'], source=check['source'], evidence=evidence,
                attempts=check['attempts'], max_attempts=check['max_attempts'])
