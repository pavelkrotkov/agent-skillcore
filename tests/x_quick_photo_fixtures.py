from pathlib import Path
from unittest.mock import patch

from test_x_media_inputs import png
from x_quick_context_fixtures import ContextCase
from x_quick_fixtures import native
from x_curator import quick_mcp, quick_photos
from x_curator.codex_runner import arguments


class PhotoCase(ContextCase):
    def setUp(self):
        super().setUp()
        self.images = {'https://example.test/a.png': png(255), 'https://example.test/b.png': png(0)}
        photos = [{'type': 'photo', 'media_url_https': url} for url in self.images]
        self.posts[0]['legacy']['extended_entities'] = {'media': photos[:1]}
        self.posts[1]['legacy']['extended_entities'] = {'media': photos}
        self.receipt_images = lambda images: images

    def exchange(self, url, **kwargs):
        self.assertEqual(kwargs, {'max_bytes': quick_photos.MAX_BYTES, 'allow_prefix': False})
        return 200, [('Content-Type', 'image/png')], self.images[url]

    def run_worker(self, body=None):
        with patch('x_curator.public_http.exchange', self.exchange), \
                patch('x_curator.readers.extract', side_effect=AssertionError('deep reader forbidden')):
            return super().run_worker(body)

    def inputs(self, request):
        args = arguments(self.db, self.root / 'runs' / self.token, 'codex', request)
        paths = [Path(args[i + 1]) for i, arg in enumerate(args) if arg == '-i']
        images = {path.stem: path.read_bytes() for path in paths}
        expected = {self.images[c['url']] for c in request['bundle']['captures'].values() if c['kind'] == 'image'}
        self.assertEqual(set(images.values()), expected)
        return images

    def checker(self, request):
        self.request = request
        images = self.inputs(request)
        capture = next(k for k, c in request['bundle']['captures'].items() if c.get('url', '').endswith('/a.png'))
        decision = {'format': 'compact-v1', 'outcome': 'supported', 'reason': 'Attributed visual humor.',
                    'claims': [{'text': 'The author shares a red-square visual joke.', 'kind': 'humor',
                                'status': 'subjective', 'attribution': 'Post author', 'limitations': [],
                                'sources': [{'capture': capture, 'quote': '', 'observation': 'A red square.',
                                             'primary': False, 'credible': False, 'origin': 'Post author',
                                             'reason': 'Observation of supplied image pixels.'}]}]}
        self.validation = quick_mcp.call(self.db, self.token, 'validate', {'decision': decision})
        return native(request, decision, [self.validation], images=self.receipt_images(images))
