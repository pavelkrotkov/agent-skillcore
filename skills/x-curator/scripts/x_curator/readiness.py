"""A missing configured reader must not consume attempts from the research cohort."""
import json
import os
from pathlib import Path

from . import provider_health
from .speech_client import request
from .deadlines import DeadlineExceeded


def blocked(db):
    provider = provider_health.blocked(db)
    if provider:
        return provider
    path = os.environ.get('X_CURATOR_SPEECH_CONFIG')
    if not path:
        return None
    try:
        config = json.loads(Path(path).read_text())
        actual = request(config, 'GET', '/health', timeout=5)
        if actual != {key: config[key] for key in ('engine_sha', 'model_sha')}:
            raise ValueError('reader profile changed')
    except DeadlineExceeded:
        raise
    except Exception as exc:
        return {'route': 'speech', 'action': 'Check qualified local speech reader and SSH tunnel: ' + type(exc).__name__}
    return None
