"""Audit historical prompt payloads without depending on today's instruction wording."""
import json

from .receipts import digest
from .storage import sha256


def verify(proof, request):
    if any(c.get('kind') == 'pdf' for c in request['bundle']['captures'].values()) and proof['format'] != 'x-curator-input-proof-v2':
        raise ValueError('PDF pages require ordered image proofs')
    expected = dict(request, proposal_sha=digest(request['proposal']))
    marker = '\nUNTRUSTED EVIDENCE AND PROPOSAL:\n'
    if request['role'] in ('organize', 'organize_review'):
        from .wiki_prompt_payload import payload as wiki_payload
        marker = '\nUNTRUSTED INPUTS:\n'
        expected = wiki_payload(request)
    payload = json.loads(proof['prompt'].partition(marker)[2])
    actual = (proof['request_sha'], proof['prompt_sha'], payload)
    if actual != (digest(request), sha256(proof['prompt'].encode()), expected):
        raise ValueError('model input proof does not match the controller request')

    from .media_inputs import input_images
    if proof['images'] != input_images(request):
        raise ValueError('model image proof does not match acquired media')


def verify_input(proof, request):
    from .rollout_guard import verify_input as verify_rollout
    verify(proof, request)
    verify_rollout(proof)
