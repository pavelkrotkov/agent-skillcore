"""Bind the qualified speech reader only to localhost for an outgoing SSH tunnel."""
from http.server import HTTPServer
import json
from pathlib import Path
from socketserver import ForkingMixIn
import sys

from .publication_files import private_target
from .speech_http import Handler


class SpeechServer(ForkingMixIn, HTTPServer):
    max_children = 2


def main(path):
    config = json.loads(Path(path).read_text())
    if len(config['token']) < 32:
        raise ValueError('speech service requires a strong private token')
    root = Path(config['state'])
    private_target(root, 'speech/probe')
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    root.chmod(0o700)
    server = SpeechServer(('127.0.0.1', 8768), Handler)
    server.config = config
    server.serve_forever()


if __name__ == '__main__':
    main(sys.argv[1])
