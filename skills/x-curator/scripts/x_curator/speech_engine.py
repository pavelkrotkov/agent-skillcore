"""Run an unchanged qualified Whisper CLI; keep actual output and stderr privately."""
import json
from pathlib import Path
import tempfile
import time

from .publication_files import write_verified
from .receipts import encoded
from .speech_protocol import duration, validate, make_receipt
from .storage import sha256
from .speech_execution import run


def transcribe(body, config):
    seconds = duration(body)
    profile(config)
    prefix = f'speech/{sha256(body)}'
    with tempfile.TemporaryDirectory(dir=config['state']) as folder:
        root = Path(folder)
        audio = root / 'audio.wav'
        audio.write_bytes(body)
        args = [config['engine'], '-m', config['model'], '-f', str(audio), '-t', '4', '-l', 'auto',
                '-bs', '1', '-bo', '1', '-oj', '-of', str(root / 'result')]
        started = time.time()
        run(args, root, config['state'], prefix)
        output = (root / 'result.json').read_bytes()
    write_verified(config['state'], f'{prefix}/output-{sha256(output)}.json', output)
    receipt = make_receipt(json.loads(output), config, body, seconds, started)
    write_verified(config['state'], f'{prefix}/receipt-{sha256(encoded(receipt))}.json', encoded(receipt))
    return validate(receipt, body, config)


def profile(config):
    for key in ('engine', 'model'):
        if sha256(Path(config[key]).read_bytes()) != config[key + '_sha']:
            raise ValueError('speech profile artifact changed')
    return {key: config[key] for key in ('engine_sha', 'model_sha')}
