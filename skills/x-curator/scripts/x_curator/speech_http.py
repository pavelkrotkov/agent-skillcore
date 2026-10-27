"""Bounded authenticated HTTP handler for the private speech reader."""
import hmac
from http.server import BaseHTTPRequestHandler
import time

from .deadlines import until
from .receipts import encoded
from .speech_engine import transcribe, profile
from .speech_audio import read


class Handler(BaseHTTPRequestHandler):
    def handle(self):
        self.connection.settimeout(10)
        with until(time.time() + 650):
            super().handle()

    def do_POST(self):
        try:
            result = self.process()
            self.send_response(200)
        except Exception as exc:
            result = {'error': type(exc).__name__}
            self.send_response(503)
        body = encoded(result)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def process(self):
        config = self.server.config
        paths = {'POST': '/transcribe', 'GET': '/health'}
        if self.path != paths.get(self.command) or not hmac.compare_digest(self.headers.get('Authorization', ''), 'Bearer ' + config['token']):
            raise ValueError('invalid speech request')
        if self.command == 'GET':
            return profile(config)
        length = int(self.headers.get('Content-Length', '0'))
        body = read(self.rfile, length)
        return transcribe(body, config)

    do_GET = do_POST

    def log_message(self, *_args):
        pass
