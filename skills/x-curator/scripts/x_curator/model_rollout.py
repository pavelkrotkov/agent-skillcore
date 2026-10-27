"""Read the private persistent rollout for the exact completed CLI session."""
from pathlib import Path
import uuid

from .model_events import result


def read(log, environment):
    session, _ = result(log)
    return read_session(session, environment)


def read_session(session, environment):
    uuid.UUID(session)
    home = Path(environment.get('CODEX_HOME', str(Path.home() / '.codex')))
    paths = list((home / 'sessions').rglob('*' + session + '*.jsonl'))
    if len(paths) != 1:
        raise ValueError('missing unique persistent model rollout')
    return paths[0].read_bytes()
