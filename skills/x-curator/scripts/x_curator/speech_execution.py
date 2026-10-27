"""Retain failed reader diagnostics before its temporary working directory disappears."""
import subprocess
import time

from .publication_files import write_verified
from .storage import sha256
from .receipts import encoded


def run(args, root, state, prefix):
    try:
        result = subprocess.run(args, capture_output=True, timeout=540, check=True)
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError) as exc:
        save(state, prefix, 'failed-stderr', exc.stderr or b'No reader stderr received.')
        save(state, prefix, 'failed-stdout', exc.stdout or b'No reader stdout received.')
        save(state, prefix, 'failure', encoded({'state': 'failed', 'error': type(exc).__name__, 'at': time.time(), 'timeout': 540}))
        partial = root / 'result.json'
        if partial.exists():
            save(state, prefix, 'partial-output', partial.read_bytes())
        raise
    save(state, prefix, 'stderr', result.stderr)
    return result


def save(state, prefix, role, body):
    write_verified(state, f'{prefix}/{role}-{sha256(body)}', body)
