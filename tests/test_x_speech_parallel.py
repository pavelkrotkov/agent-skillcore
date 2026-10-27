from concurrent.futures import ThreadPoolExecutor
from http.client import HTTPConnection
import json
import multiprocessing
import os
import unittest
from unittest.mock import patch

from test_x_speech import audio
from x_curator.speech_server import SpeechServer
from x_curator.speech_http import Handler


class ParallelSpeechTests(unittest.TestCase):
    def test_two_authenticated_readers_execute_with_independent_deadlines(self):
        context = multiprocessing.get_context('fork')
        barrier = context.Barrier(2)
        server = SpeechServer(('127.0.0.1', 0), Handler)
        server.config = {'token': 'synthetic-private-token'}
        process = context.Process(target=server.serve_forever)
        with patch('x_curator.speech_http.transcribe', side_effect=lambda *_: (barrier.wait(5), {'pid': os.getpid()})[1]):
            process.start()
        try:
            with ThreadPoolExecutor(max_workers=2) as workers:
                replies = list(workers.map(lambda _: self.request(server.server_port), range(2)))
            self.assertEqual(len({r['pid'] for r in replies}), 2)
            self.assertNotIn(process.pid, {r['pid'] for r in replies})
        finally:
            process.terminate()
            process.join(10)
            server.server_close()

    def request(self, port):
        connection = HTTPConnection('127.0.0.1', port, timeout=10)
        try:
            connection.request('POST', '/transcribe', body=audio(), headers={'Authorization': 'Bearer synthetic-private-token'})
            response = connection.getresponse()
            self.assertEqual(response.status, 200)
            return json.loads(response.read())
        finally:
            connection.close()
