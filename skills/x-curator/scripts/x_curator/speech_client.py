"""Read private speech over a fixed loopback SSH forward, never an arbitrary URL."""
from http.client import HTTPConnection
import json
from pathlib import Path

from .receipts import encoded
from .speech_protocol import validate


def transcribe(audio, config_path):
    config = json.loads(Path(config_path).read_text())
    body = Path(audio).read_bytes()
    receipt = request(config, 'POST', '/transcribe', body)
    return encoded(validate(receipt, body, config)).decode()


def request(config, method, path, body=None, timeout=570):
    connection = HTTPConnection('127.0.0.1', 8768, timeout=timeout)
    try:
        connection.request(method, path, body=body, headers={'Authorization': 'Bearer ' + config['token']})
        response = connection.getresponse()
        raw = response.read(2 * 1024 * 1024 + 1)
        if response.status != 200 or len(raw) > 2 * 1024 * 1024:
            raise ValueError('qualified speech service unavailable; inspect private reader logs')
        return json.loads(raw)
    finally:
        connection.close()
