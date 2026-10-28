from contextlib import contextmanager
import subprocess
import sys
from unittest.mock import patch

from x_curator.command_lock import lockfile


@contextmanager
def competing_index(root, seconds):
    script = '''import fcntl, sys, time
with open(sys.argv[1], 'a') as lock:
    fcntl.flock(lock, fcntl.LOCK_EX)
    print('locked', flush=True)
    time.sleep(float(sys.argv[2]))
'''
    with subprocess.Popen([sys.executable, '-c', script, str(root / '.wiki.lock'), str(seconds)],
                          stdout=subprocess.PIPE, text=True) as process:
        try:
            if process.stdout.readline().strip() != 'locked':
                raise RuntimeError('synthetic index failed to acquire lock')
            yield
        finally:
            process.terminate()
            process.wait(timeout=5)


@contextmanager
def contend(root, module, seconds):
    @contextmanager
    def acquire(root, name, **options):
        if name != '.wiki.lock':
            with lockfile(root, name, **options):
                yield
            return
        with competing_index(root, seconds), lockfile(root, name, **options):
            yield
    with patch(f'x_curator.{module}.lockfile', acquire):
        yield

