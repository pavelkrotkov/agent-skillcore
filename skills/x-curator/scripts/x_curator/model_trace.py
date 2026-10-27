"""Versioned controller envelopes preserve unchanged native execution evidence."""
import json
from marshal import dumps, loads
from functools import lru_cache

from .receipts import digest, encoded
from .media_inputs import input_images
from .model_input_binding import verify as verify_payload, verify_input
from .storage import sha256

FORMAT = 'x-curator-input-proof-v2'


def records(log):
    return loads(decoded(log))


@lru_cache(maxsize=8)
def decoded(log):
    return dumps([json.loads(line) for line in log.decode().split('\n') if line.strip()])


def envelope(log):
    rows = records(log)
    return rows[0] if len(rows) == 1 and rows[0].get('format') in ('x-curator-input-proof-v1', FORMAT) else None


def native(log):
    return loads(verified_native(log))


@lru_cache(maxsize=8)
def verified_native(log):
    proof = envelope(log)
    if proof is None:
        return dumps(records(log))
    from .rollout_guard import verify
    events = records(proof['events'].encode())
    verify(proof)
    return dumps(events)


def pack(request, prompt, args, events, rollout):
    value = {'format': FORMAT, 'request_sha': digest(request), 'prompt_sha': sha256(prompt.encode()),
             'profile': args, 'prompt': prompt, 'images': input_images(request),
             'events': events.decode(), 'rollout': rollout.decode()}
    log = encoded(value)
    verify_request(log, request)
    return log


def verify_request(log, request):
    proof = envelope(log)
    if proof is not None:
        verify_payload(proof, request)
        native(log)
