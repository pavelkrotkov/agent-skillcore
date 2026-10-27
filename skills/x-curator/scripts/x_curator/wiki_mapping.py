"""Only separately reviewed, authentic model events can classify source claims."""

from . import wiki_store, provider_health, execution_failure
from .codex_runner import runner
from .deadlines import until, DeadlineExceeded
from .model_events import result
from .wiki_contract import validate
from .wiki_final import output
from .wiki_mapping_receipts import accept
from .wiki_mapping_feedback import previous_rejection
from .worker_errors import WorkerFailure
from .wiki_prompts import preflight, request as model_request
from .wiki_catalog_recovery import prepare
from .stage_timings import span


def organize(db, current, pages, selected):
    try:
        map_sources(db, prepare(db, current, pages, selected))
    except (ValueError, RuntimeError, KeyError, TypeError) as exc:
        return f'{type(exc).__name__}: {str(exc)[:300]}'


def map_sources(db, inputs):
    if provider_health.blocked(db):
        raise WorkerFailure('provider route cooling down; inspect provider_health', b'')
    feedback = previous_rejection(db, inputs)
    if feedback:
        inputs = dict(inputs, feedback=feedback)
    preflight(inputs)
    identity = wiki_store.reserve(db, inputs)
    expires = db.execute('SELECT expires FROM wiki_runs WHERE id=?', (identity,)).fetchone()[0]
    try:
        with until(expires):
            call = runner(db, identity)
            packet = invoke(db, identity, 'proposal', inputs, call)
            validate(packet, inputs)
            invoke(db, identity, 'review', inputs, call, packet)
            accept(db, identity)
    except Exception as exc:
        if failure := execution_failure.provider_failure(exc, getattr(exc, 'log', b'')):
            provider_health.suspend(db, failure)
        wiki_store.fail(db, identity, f'{type(exc).__name__}: {str(exc)[:300]}')
        raise
    return identity


def invoke(db, identity, role, inputs, call, proposal=None):
    request = model_request('organize' if role == 'proposal' else 'organize_review', inputs, proposal)
    with span(db, 'wiki.organization.' + role, mapping=identity,
              model='gpt-5.6-sol', provider='ChatGPT', reasoning='high'):
        try:
            log = call(request)
        except (WorkerFailure, DeadlineExceeded) as exc:
            wiki_store.receipt(db, identity, role, getattr(exc, 'log', b''))
            raise
        wiki_store.receipt(db, identity, role, log)
        return output(log, inputs) if role == 'proposal' else result(log)[1]
