"""Long-running workers use database leases so intake remains available concurrently."""
from contextlib import contextmanager
import fcntl


@contextmanager
def command_lock(args):
    if args.command in ("work", "report", "batches", "review", "research", "policy-report", "retain"):
        yield True
        return
    name = {'wiki': '.wiki.lock', 'zk-refresh': '.wiki.lock', 'index-pending': '.wiki.lock', 'recover-wiki': '.wiki.lock', 'supervise': '.supervisor.lock', 'complete-publication': '.publication-recovery.lock'}.get(args.command, '.collector.lock')
    with lockfile(args.state, name, defer=args.command == "index-pending") as acquired:
        yield acquired


@contextmanager
def lockfile(root, name, *, blocking=False, defer=False):
    with (root / name).open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | (0 if blocking else fcntl.LOCK_NB))
        except BlockingIOError:
            if not defer:
                raise
            yield False
            return
        yield True
