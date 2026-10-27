"""A fixed ChatGPT subscription route; provider failures never switch billing paths."""
import shutil

from . import blobs, model_rollout, model_trace, native_search, quick_profile, quick_final_profile
from .codex_profile import command, environment as profile_environment, login_status
from .media_inputs import attachments, deferred
from .worker_errors import WorkerFailure
from .process_group import execute
from .worker_prompts import prompt
from .receipts import digest


def runner(db, token):
    binary = shutil.which("codex")
    if binary is None:
        raise WorkerFailure("Codex CLI unavailable; no provider fallback", b"")
    environment = profile_environment()
    login_status(binary, environment)
    root = blobs.state_root(db) / "runs" / token
    root.mkdir(parents=True, mode=0o700, exist_ok=True)
    return quick_profile.checker(db, root, binary, environment)


def arguments(db, root, binary, request):
    phase = request.get('phase', {}).get('name')
    args = command(binary, phase != 'final' and (request["role"] == "discover" or native_search.enabled(request)))
    for path in ([] if deferred(request) else attachments(db, root, request['bundle'], request.get('image_presentations'))):
        args.extend(["-i", str(path)])
    quick_profile.configure(args, db, root.name, request['role'], native_search.enabled(request), request.get('linked', False), phase=phase)
    quick_final_profile.configure(args, root, request)
    return args + ['-']


def run(db, root, binary, environment, request):
    rendered, args = prompt(request), arguments(db, root, binary, request)
    output = root / (digest(request) + ".jsonl")
    with output.open("xb") as stdout, output.with_suffix(".stderr").open("xb") as stderr:
        code = execute(args, rendered.encode(), request, output=output, cwd=root, env=environment, stdout=stdout, stderr=stderr)
    log = output.read_bytes()
    if code:
        raise WorkerFailure("subscription provider unavailable; inspect private execution receipt", log)
    return model_trace.pack(request, rendered, args, log, model_rollout.read(log, environment))
