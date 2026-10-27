"""Wall-clock limits include DNS, slow streams, readers and child processes."""
from contextlib import contextmanager
import signal
import time


class DeadlineExceeded(Exception):
    pass


def expired(_signal, _frame):
    raise DeadlineExceeded("execution deadline exhausted; recover unfinished source")


@contextmanager
def until(deadline):
    remaining = deadline - time.time()
    if remaining <= 0:
        raise DeadlineExceeded("persisted attempt deadline exhausted")
    previous = signal.getsignal(signal.SIGALRM)
    started = time.monotonic()
    timer = signal.setitimer(signal.ITIMER_REAL, 0)
    signal.signal(signal.SIGALRM, expired)
    seconds = min(remaining, timer[0]) if timer[0] else remaining
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)
        if timer[0]:
            signal.setitimer(signal.ITIMER_REAL, max(0.001, timer[0] - (time.monotonic() - started)), timer[1])
