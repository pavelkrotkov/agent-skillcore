"""An explicit command is the only entry to one consumed, bounded research run."""
from .stage_timings import timed
from . import deep_claim, deep_permission, deep_store, execution_failure, native_search, quick_context, quick_proof
from .codex_profile import MODEL
from .codex_runner import runner
from .deadlines import until
from .evidence import bundle
from .executions import recorded
from .publication import publish
from .quick_sources import register
from .receipts import digest
from .research import output


def work(db, state, identity):
    job = deep_claim.claim(db, identity)
    if job is None:
        return {'state': 'blocked', 'reason': 'Both source-worker slots are occupied; approval remains unspent.'}
    try:
        with until(job['deadline']):
            return run(db, state, job)
    except Exception as exc:
        execution_failure.record(db, state, job['token'], exc)
        reason = 'Approved research unresolved: ' + type(exc).__name__ + ': ' + str(exc)[:400]
        deep_store.finish(db, job['token'], 'inconclusive', reason)
        return {'state': 'awaiting_review', 'approval': identity, 'reason': reason}


@timed("research.approved", scope="selected")
def run(db, state, job):
    token = job['token']
    _, proposal = deep_permission.verified(db, job['approval'])
    quick_context.capture(db, token)
    from .deep_resource import acquire
    resource = acquire(db, token, job['approval'])
    evidence = bundle(db, token)
    request = dict(role='factcheck', policy=deep_store.POLICY, approval=job['approval'], deadline=job['deadline'],
                   question=job['question'], scope=job['scope'], resource=resource, search_mode=native_search.research_mode(proposal), sources=register(db, token, evidence),
                   bundle=evidence, bundle_sha=digest(evidence), proposal=None)
    execution = recorded(db, token, 'factcheck', MODEL, runner(db, token), request)
    decision = output(db, execution)
    quick_proof.decision_proof(db, token, execution, bundle(db, token))
    if decision['outcome'] == 'supported':
        identity = publish(db, state, token, execution, execution)
        return {'state': 'published', 'publication': identity, 'approval': job['approval']}
    deep_store.finish(db, token, decision['outcome'], decision['reason'], execution)
    return {'state': 'excluded' if decision['outcome'] == 'disproven' else 'awaiting_review', 'approval': job['approval']}
