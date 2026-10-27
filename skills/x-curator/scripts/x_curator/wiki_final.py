"""A completed compact answer selects its exact successful same-execution draft."""
import json

from .model_events import result
from .model_trace import envelope, verify_request
from .wiki_final_events import validations, selected
from .quick_final import FORMAT
from .receipts import digest, encoded
from .verification_details import hash_label
from .wiki_contract import validate
from .wiki_notes import request
from .wiki_references import canonical

INSTRUCTIONS = '''The supplied final_format avoids repeating a validated proposal. Send the complete
proposal to validate. Correct errors within this execution. Once valid, immediately return the tool's
final_answer object verbatim: {format:'curator-validated-decision-v1',decision_sha:'controller hash'}.
Do not calculate a hash, repeat the proposal, search again or revalidate an unchanged passing draft.
The final reference selects that exact proposal; a completed final turn, full validation and independent
review are still required. This contract grants no additional time, attempt or research allowance.
'''


def feedback(inputs, proposal):
    if inputs.get('final_format') != FORMAT:
        return 'Valid draft. Final validation and independent review are still required.'
    final = dict(format=FORMAT, decision_sha=digest(proposal))
    return encoded(dict(valid=True, decision_sha=final['decision_sha'], final_answer=final,
                        next_action='Return final_answer verbatim now. Independent review is still required.')).decode()


def contract(value, inputs, log):
    if (inputs.get('final_format') != FORMAT or set(value) != {'format', 'decision_sha'}
            or hash_label(value['decision_sha']) == 'invalid' or envelope(log) is None):
        raise ValueError('wiki final reference requires its explicit authenticated output contract')
    verify_request(log, request('organize', inputs))


def output(log, inputs):
    _, value = result(log)
    if not isinstance(value, dict) or value.get('format') != FORMAT:
        return canonical(value, inputs)
    contract(value, inputs, log)
    for item in validations(log):
        proposal = selected(item, value['decision_sha'], inputs)
        if proposal is not None:
            validate(proposal, inputs)
            return proposal
    raise ValueError('wiki final reference has no matching successful validation in this execution')
