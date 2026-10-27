"""HTTP boundaries against synthetic generations, never the live corpus."""
import http.client
import json
from pathlib import Path
import tempfile
import threading
import unittest

from x_fixtures import SCRIPTS
from x_curator.wiki_http import Handler, ThreadingHTTPServer


class WikiHTTPTests(unittest.TestCase):
    def test_rollover_and_private_path_boundaries(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            wiki = root / 'wiki'
            for generation in ('a' * 64, 'b' * 64):
                site = wiki / 'builds' / generation / 'site'
                site.mkdir(parents=True)
                (site / 'index.html').write_text(generation)
                (site / 'search').mkdir()
                (site / 'search/search_index.json').write_text('{"docs":[]}')
                (site / 'escape').symlink_to(root / 'secret')
                (site / 'directory').mkdir()
                # The stdlib opens index.html after translating the directory, bypassing a file-only fence.
                (site / 'directory/index.html').symlink_to(root / 'secret')
                (site / 'empty').mkdir()
            (root / 'secret').write_text('PRIVATE')
            pointer = wiki / 'CURRENT.json'
            pointer.write_text(json.dumps({'generation': 'a' * 64}))
            with ThreadingHTTPServer(('127.0.0.1', 0), Handler) as server:
                server.root = root
                thread = threading.Thread(target=server.serve_forever)
                thread.start()
                try:
                    self.assertEqual(self.get(server, '/'), (200, 'a' * 64))
                    pointer.write_text(json.dumps({'generation': 'b' * 64}))
                    self.assertEqual(self.get(server, '/'), (200, 'b' * 64))
                    self.assertEqual(self.get(server, '/search/search_index.json'), (200, '{"docs":[]}'))
                    for path in ('/escape', '/directory/', '/empty/', '/index.html/../../secret', '/CURRENT.json'):
                        status, body = self.get(server, path)
                        self.assertIn(status, (403, 404))
                        self.assertNotIn('PRIVATE', body)
                    for value in ('../../..', None, 'c' * 64):
                        pointer.write_text(json.dumps({'generation': value}))
                        self.assertEqual(self.get(server, '/')[0], 503)
                    pointer.write_text('{')
                    self.assertEqual(self.get(server, '/')[0], 503)
                finally:
                    server.shutdown()
                    thread.join()

    def get(self, server, path):
        connection = http.client.HTTPConnection(*server.server_address)
        try:
            connection.request('GET', path)
            response = connection.getresponse()
            self.assertEqual(response.getheader('Cache-Control'), 'no-cache')
            return response.status, response.read().decode()
        finally:
            connection.close()
