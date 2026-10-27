"""The default is one bounded checker; approval-gated deep research is separate."""
from .stage_timings import timed
import time

from . import codex_profile, executions, execution_failure, native_search, quick_context, quick_linked, quick_phases, quick_proof, quick_store
from .codex_runner import runner
from .deadlines import until
from .evidence import bundle
from .publication import publish
from .quick_final import output

SEARCH_MODE = native_search.MODE


def research(db, state, client, token):
    started = time.time()
    try:
        with until(started + 120):
            check = quick_store.start(db, token, started)
        with until(check['deadline']):
            return run(db, state, client, token, check)
    except Exception as exc:
        execution_failure.record(db, state, token, exc)
        reason = 'Quick check inconclusive: ' + type(exc).__name__ + ': ' + str(exc)[:400]
        quick_store.finish(db, token, 'inconclusive', reason)
        return None


@timed("research.quick", scope="selected")
def run(db, state, client, token, check):
    if check['outcome'] is not None:
        raise ValueError('this revision already has a quick-check disposition')
    selection, evidence = quick_context.capture(db, token, client), bundle(db, token)
    linked = quick_linked.capture(db, token, evidence['captures'][selection])
    if linked is False:
        quick_store.finish(db, token, 'inconclusive', 'Linked source body did not provide usable text evidence.')
        return None
    request = quick_linked.request(db, token, check, bundle(db, token), SEARCH_MODE)
    executor = runner(db, token)
    request = quick_phases.prepare(db, token, executor, request, check)
    execution = executions.recorded(db, token, 'factcheck', codex_profile.MODEL, executor, request)
    decision = output(db, execution)
    quick_proof.decision_proof(db, token, execution, bundle(db, token))
    if decision['outcome'] == 'supported':
        return publish(db, state, token, execution, execution)
    quick_store.finish(db, token, decision['outcome'], decision['reason'], execution)
    return None
