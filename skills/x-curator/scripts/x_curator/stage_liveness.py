"""Process-liveness state for interrupted private spans."""
import os
from .process_liveness import start_mark

def process_state(row, marker):
    try:
        os.kill(row['pid'], 0)
    except ProcessLookupError:
        return 'interrupted'
    except PermissionError:
        return 'unverified'
    return 'running' if marker and marker == row['process_start'] else 'unverified'



def interrupted(row):
    if row['finished'] is not None:
        return row['outcome']
    if row['pid'] == os.getpid():
        return 'running'
    marker = start_mark(row['pid'])
    if row['process_start'] and marker and marker != row['process_start']:
        return 'interrupted'
    return process_state(row, marker)
