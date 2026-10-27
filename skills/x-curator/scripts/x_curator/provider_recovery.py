"""Fresh complete execution proofs can release only their observed failure generation."""
from datetime import datetime
import time

from .model_trace import envelope, records, verify_request
from .provider_health import current, release


def invoke(db, root, binary, environment, request):
    from .codex_runner import run, arguments
    failure = current(db)
    started = time.time()
    log = run(db, root, binary, environment, request)
    if failure:
        recover(db, failure, started, request, log, arguments(db, root, binary, request))
    return log


def verify(failure, started, request, log, profile):
    proof = envelope(log)
    if proof is None or proof['profile'] != profile:
        raise ValueError('provider recovery requires the fixed complete execution profile')
    verify_request(log, request)
    meta = next(row['payload'] for row in records(proof['rollout'].encode()) if row['type'] == 'session_meta')
    native_start = datetime.fromisoformat(meta['timestamp'].replace('Z', '+00:00'))
    now = time.time()
    if native_start.tzinfo is None or not failure['failed_at'] < started <= native_start.timestamp() <= now:
        raise ValueError('provider recovery requires a fresh native session after the observed failure')
    return now


def recover(db, failure, started, request, log, profile):
    if not failure or failure['generation'] is None or failure['failed_at'] is None:
        return False
    now = verify(failure, started, request, log, profile)
    return release(db, failure, started, now, log)
