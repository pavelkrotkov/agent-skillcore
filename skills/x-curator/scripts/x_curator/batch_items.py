"""Review proposals retain unresolved assertions without turning failures into facts."""
from .quick_final import output


def item(db, row, failures):
    value = dict(source=row['id'], reference=row['batch'] + ':' + row['id'], state=disposition(row, failures), reason=row['action'], retrieval_failures=failures)
    if row['outcome']:
        value.update(revision=row['revision'], searches=row['searches'], check=row['check_id'])
    if value['state'] == 'pending_decision':
        decision = output(db, row['execution'])
        questions = [c['text'] for c in decision.get('checks', []) if c['status'] == 'inconclusive']
        value.update(question='Check: ' + '; '.join(questions or [decision['reason']]),
                     scope='Targeted evidence for the unresolved claim; no full books or videos.', seconds=600)
    return value


def disposition(row, failures):
    if row['state'] == 'published':
        return 'supported'
    if row['state'] == 'excluded':
        return 'excluded'
    if row['state'] == 'awaiting_review':
        return pending_state(row, failures)
    if row['state'] == 'needs_action':
        return 'failed_processing'
    return 'processing'


def pending_state(row, failures):
    checked = not failures and row['execution'] and row['outcome'] == 'inconclusive' and row['action'] == row['reason']
    return 'pending_decision' if checked else 'failed_processing'
