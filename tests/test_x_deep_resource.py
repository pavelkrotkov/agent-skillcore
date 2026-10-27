import json
import time
from unittest.mock import patch

from x_deep_fixtures import DeepCase
from x_curator import deep_review


class DeepResourceTests(DeepCase):
    def approve_video(self, seconds=600):
        self.authorize()
        self.deep()
        account = self.db.execute('SELECT account FROM research_permissions').fetchone()[0]
        resource = {'kind': 'video', 'url': 'https://example.test/approved.mp4'}
        self.value = deep_review.prepare(self.db, account, 'synthetic-chat', self.approval, seconds, resource)
        reference = json.loads(self.value['payload'])['review'][0]['reference']
        self.observe()
        self.reply('research ' + reference, identity='explicit-video')
        self.approval = self.db.execute('SELECT id FROM research_permissions WHERE consumed IS NULL').fetchone()[0]

    def test_optional_reader_runs_only_for_exact_separately_approved_url(self):
        self.approve_video()
        fetch = lambda url: (200, 'video/mp4', b'Synthetic video fixture', None)
        def extract(db, payload):
            return dict(payload, kind='video', text='Synthetic machine transcript.', images=[],
                        required_urls=['https://example.test/unapproved.pdf'], limitations=['Synthetic sampled-video limitation'])
        with patch('x_curator.deep_resource.public_http.fetch', fetch), patch('x_curator.deep_resource.readers.extract', extract), patch('x_curator.acquire.acquire_urls', side_effect=AssertionError('recursive acquisition forbidden')):
            self.assertEqual(self.deep()['state'], 'awaiting_review')
        requests = [row['url'] for row in self.db.execute('SELECT url FROM retrievals WHERE token=(SELECT token FROM deep_runs WHERE id=?)', (self.approval,))]
        self.assertEqual(requests, ['https://example.test/approved.mp4'])

    def test_reader_timeout_spends_original_allowance_without_starting_model(self):
        self.approve_video(seconds=1)
        def slow(db, payload):
            time.sleep(2)
            raise AssertionError('reader should have been interrupted')
        fetch = lambda url: (200, 'video/mp4', b'Synthetic video fixture', None)
        self.checker = lambda request: self.fail('model started after reader deadline')
        started = time.monotonic()
        with patch('x_curator.deep_resource.public_http.fetch', fetch), patch('x_curator.deep_resource.readers.extract', slow):
            result = self.deep()
        self.assertEqual(result['state'], 'awaiting_review')
        self.assertIn('DeadlineExceeded', result['reason'])
        self.assertLess(time.monotonic() - started, 2)
        with self.assertRaises(ValueError):
            self.deep()
