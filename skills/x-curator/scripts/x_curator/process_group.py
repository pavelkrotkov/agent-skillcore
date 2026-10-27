"""A deadline terminates the model and its tool children, not just the CLI parent."""
import os
import signal
import subprocess
import time

from .deadlines import DeadlineExceeded, until
from .worker_errors import WorkerFailure


def run(args, content, **kwargs):
    with subprocess.Popen(args, stdin=subprocess.PIPE, start_new_session=True, **kwargs) as process:
        try:
            process.communicate(content)
        except BaseException:
            terminate(process)
            raise
        return process.returncode


def terminate(process):
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    process.wait()


def execute(args, content, request, output=None, **kwargs):
    from .codex_profile import execution_timeout
    try:
        if request['role'] == 'factcheck':
            with until(request['deadline']):
                return run(args, content, **kwargs)
        if request.get('bundle', {}).get('wiki_inputs', {}).get('organization') == 'zettelkasten/v1':
            with until(time.time() + execution_timeout(request)):
                return run(args, content, **kwargs)
        return subprocess.run(args, input=content, timeout=execution_timeout(request), **kwargs).returncode
    except (subprocess.TimeoutExpired, OSError, DeadlineExceeded) as exc:
        exc.log = output.read_bytes() if output else b''
        if isinstance(exc, DeadlineExceeded):
            raise
        raise WorkerFailure('subscription execution unavailable: ' + type(exc).__name__, exc.log) from exc
