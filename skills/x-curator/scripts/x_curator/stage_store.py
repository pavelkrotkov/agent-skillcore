"""Private WAL stage receipts survive corpus transactions and crashes."""
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
import sqlite3
import subprocess
import os
import threading

_SCHEMA = '''CREATE TABLE IF NOT EXISTS stage_spans (
    id TEXT PRIMARY KEY, run TEXT NOT NULL, parent TEXT, stage TEXT NOT NULL,
    started TEXT NOT NULL, finished TEXT, monotonic_start REAL NOT NULL,
    elapsed REAL, process_cpu_seconds REAL, outcome TEXT NOT NULL, failure TEXT,
    context TEXT NOT NULL, pid INTEGER NOT NULL, process_start TEXT)'''

def path(db):
    raw = getattr(db, 'db', db)
    return Path(raw.execute('PRAGMA database_list').fetchone()[2]).parent / 'stage-spans.sqlite3'


def initialize(db):
    target = path(db)
    for suffix in ('', '-wal', '-shm', '-journal'):
        if Path(str(target) + suffix).is_symlink():
            raise ValueError('stage receipt files must not be symlinks')
    with sqlite3.connect(target, timeout=5) as sink:
        sink.execute('PRAGMA journal_mode=WAL')
        sink.execute('PRAGMA synchronous=FULL')
        sink.execute(_SCHEMA)
    target.chmod(0o600)


def utc():
    return datetime.now(timezone.utc).isoformat()


@lru_cache(maxsize=1)
def revision():
    try:
        root = Path(__file__).resolve().parents[4]
        command = subprocess.run(['git', '-C', str(root), 'rev-parse', 'HEAD'], capture_output=True, timeout=2)
        return command.stdout.decode().strip() if command.returncode == 0 else 'unknown'
    except (OSError, subprocess.TimeoutExpired):
        return 'unknown'


_LOCAL = threading.local()


def write(db, statement, parameters):
    target = path(db)
    key = (os.getpid(), target)
    if getattr(_LOCAL, 'key', None) != key:
        previous = getattr(_LOCAL, 'connection', None)
        if previous is not None:
            previous.close()
        _LOCAL.connection = sqlite3.connect(target, timeout=5, isolation_level=None)
        _LOCAL.key = key
    _LOCAL.connection.execute(statement, parameters)
