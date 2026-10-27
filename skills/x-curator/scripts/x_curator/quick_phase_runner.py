"""Cancel acquisition at its cutoff; retain its real input without inventing a final turn."""
import time

from . import execution_failure, model_trace, model_rollout
from .deadlines import DeadlineExceeded, until
from .process_group import execute
from .receipts import digest
from .worker_errors import WorkerFailure
from .worker_prompts import prompt


def rollout(log, environment):
    sessions = [r['thread_id'] for r in model_trace.records(log) if r['type'] == 'thread.started']
    if len(sessions) != 1:
        raise ValueError('evidence phase needs one real native session')
    return model_rollout.read_session(sessions[0], environment)


def capture(db, root, binary, environment, request):
    from .codex_runner import arguments
    rendered, args = prompt(request), arguments(db, root, binary, request)
    path = root / (digest(request) + '.jsonl')
    cutoff = request['phase']['cutoff']
    status = 'completed'
    try:
        with path.open('xb') as stdout, path.with_suffix('.stderr').open('xb') as stderr:
            with until(cutoff):
                code = execute(args, rendered.encode(), request, output=path, cwd=root,
                               env=environment, stdout=stdout, stderr=stderr)
        if code:
            raise WorkerFailure('evidence-phase provider failed', path.read_bytes())
    except DeadlineExceeded as exc:
        if time.time() >= request['deadline'] or execution_failure.transport_exhausted(path.read_bytes()):
            exc.log = path.read_bytes()
            raise
        status = 'cutoff'
    stopped, events = time.time(), path.read_bytes()
    proof = dict(format=model_trace.FORMAT, request_sha=digest(request), prompt_sha=digest_text(rendered),
                 prompt=rendered, profile=args, images=model_trace.input_images(request),
                 events=events.decode(), rollout=rollout(events, environment).decode())
    model_trace.verify_input(proof, request)
    return dict(status=status, stopped=stopped, ended=time.time(), input_proof=proof)


def digest_text(text):
    from .storage import sha256
    return sha256(text.encode())
