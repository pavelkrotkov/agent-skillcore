"""The wiki is structured synthesis, never an invented cross-source consensus."""
from .receipts import encoded
from .worker_prompts import COMMON
from .wiki_zk_prompt import instructions, MAPPING, ORGANIZE, VERIFY
from .wiki_notes import request
from .wiki_prompt_payload import payload

LIMIT = 1000000
PROPOSAL_LIMIT = 100000


def prompt(request):
    inputs = request['bundle']['wiki_inputs']
    data = payload(request)
    instruction = ORGANIZE if request['role'] == 'organize' else VERIFY
    instruction += instructions(inputs, request.get('final_format'))
    text = COMMON + MAPPING + instruction + '\nUNTRUSTED INPUTS:\n' + encoded(data).decode()
    if len(text) > LIMIT:
        raise ValueError('wiki batch/catalog exceeds model envelope; reduce or partition before retry')
    return text


def preflight(inputs):
    author = LIMIT - len(prompt(request('organize', inputs)))
    review = LIMIT - PROPOSAL_LIMIT - len(prompt(request('organize_review', inputs)))
    if review < 0:
        raise ValueError('wiki batch/catalog leaves insufficient independent-review headroom')
    return min(author, review)


def proposal_capacity(packet, inputs):
    if inputs.get('projection', 0) not in (0, 1):
        raise ValueError('unknown wiki input projection')
    if inputs.get('projection') == 1 and len(encoded(packet).decode()) > PROPOSAL_LIMIT:
        raise ValueError('wiki proposal exceeds reserved review allowance')
