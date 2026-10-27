"""A Linux process-start identity distinguishes a running process from a stale PID."""
from pathlib import Path


def start_mark(pid):
    try:
        value = (Path('/proc') / str(pid) / 'stat').read_text().rsplit(')', 1)[1].split()
        return value[19] if value[0] != 'Z' else None
    except (OSError, IndexError):
        return None


def state(row):
    if row['finished'] is not None:
        return 'finished'
    actual = start_mark(row['pid'])
    if actual is None or row['process_start'] is None:
        return 'unverified'
    return 'running' if actual == row['process_start'] else 'stopped'
