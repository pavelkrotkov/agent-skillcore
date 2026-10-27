"""Bind the one checker to its initial context and the exact dynamic evidence it saw."""

from . import native_search_proof, quick_store
from .executions import verified_execution
from .quick_final import output
from .quick_phase_tools import observed, allowance as phase_allowance


def verify(db, token, proposal, review, evidence):
    packet = decision_proof(db, token, proposal, evidence)
    if proposal != review or packet is None:
        raise ValueError('fact-check did not support publication')
    return packet, evidence


def decision_proof(db, token, proposal, evidence):
    execution, request, _ = verified_execution(db, proposal, 'factcheck', token)
    from .deep_proof import allowance as bounded_allowance
    bounded_allowance(db, token, execution, request)
    initial = request['bundle']
    if (initial['account'], initial['source']) != (evidence['account'], evidence['source']):
        raise ValueError('foreign quick-check context')
    seen = dict(initial['captures'])
    observed(db, token, execution, request, seen)
    native_search_proof.sources(request, execution['log'], seen)
    if seen != evidence['captures']:
        raise ValueError('fact-checker did not see exactly the retained evidence')
    from .media_presentations import packet
    return packet(db, request, output(db, proposal), evidence)




def allowance(check, execution, request):
    if check is None or request.get('policy') != quick_store.POLICY:
        raise ValueError('explicit single-checker policy required')
    if not check['started'] <= execution['started'] <= execution['finished'] <= check['deadline']:
        raise ValueError('fact-check exceeded its durable allowance')
    phase_allowance(check, execution, request)
    if (request['check'],request['deadline']) != (check['id'],check['deadline']):
        raise ValueError('fact-check allowance binding changed')
