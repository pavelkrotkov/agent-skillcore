"""Two native executions share one source attempt and its original persisted allowance."""
import json
import time
import uuid

from . import quick_linked, quick_store
from .codex_profile import MODEL
from .evidence import bundle
from .executions import record_log
from .leases import require_lease
from .receipts import digest, encoded

MODE = 'captured-phase/v1'


def presented(db, request):
    from .media_presentations import prepare
    presentations = prepare(db, request['bundle'])
    return dict(request, image_presentations=presentations) if presentations else request


def acquire(db, token, executor, request):
    identity = uuid.uuid4().hex
    with db:
        db.execute('BEGIN IMMEDIATE')
        require_lease(db, token, time.time())
        db.execute('INSERT INTO executions(id,token,role,model,input,input_sha,started) VALUES(?,?,?,?,?,?,?)',
                   (identity, token, 'factcheck_evidence', MODEL, encoded(request).decode(), digest(request), time.time()))
    try:
        receipt = executor.evidence(request)
    except Exception as exc:
        record_log(db, identity, getattr(exc, 'log', b''))
        raise
    record_log(db, identity, receipt['input_proof']['events'].encode())
    with db:
        db.execute('UPDATE executions SET finished=?,output=?,output_sha=? WHERE id=?',
                   (receipt['ended'], encoded(receipt).decode(), digest(receipt), identity))
    return identity


def prepare(db, token, executor, request, check):
    if not hasattr(executor, 'evidence'):
        return request
    initial = dict(request, phase=dict(name='evidence', cutoff=min(check['deadline'], check['started'] + 80),
                                      image_policy='deferred-to-final'))
    initial.pop('final_format', None)
    identity = acquire(db, token, executor, initial)
    current = quick_store.active(db, token)
    final = quick_linked.request(db, token, current, bundle(db, token), MODE)
    final = presented(db, dict(final, linked=True, phase=dict(name='final', evidence_execution=identity)))
    final['proposal'] = draft(db, identity)
    from .quick_phase_proof import verify
    verify(db, token, final)
    return final


def draft(db, identity):
    from .model_events import result
    row = db.execute('SELECT log FROM executions WHERE id=?', (identity,)).fetchone()
    try:
        return result(row['log'])[1]
    except ValueError:
        return None
