from unittest.mock import patch

from x_wiki_fixtures import WikiCase
from x_curator import provider_health
from x_curator.deadlines import DeadlineExceeded
from x_curator.receipts import encoded
from x_curator.wiki_mapping import map_sources
from x_curator.worker_errors import WorkerFailure


RATE_LIMIT = encoded({'type': 'error', 'message':
    'Reconnecting... 1/5 (exceeded retry limit, last status: 429 Too Many Requests, request id: synthetic)'}) + b'\n'


class WikiProviderDeadlineTests(WikiCase):
    def check_cooldown(self, role):
        error = DeadlineExceeded('execution deadline exhausted')
        error.log = RATE_LIMIT

        def model(request):
            if request['role'] == role:
                raise error
            return self.model(request)

        with patch('x_curator.wiki_mapping.runner', return_value=model):
            with self.assertRaises(DeadlineExceeded):
                map_sources(self.db, self.inputs)
        row = self.db.execute('SELECT * FROM wiki_runs').fetchone()
        column = 'proposal' if role == 'organize' else 'review'
        self.assertEqual((row['state'], row[column]), ('failed', RATE_LIMIT))
        self.assertIsNotNone(provider_health.blocked(self.db))
        with patch('x_curator.wiki_mapping.runner') as runner:
            with self.assertRaises(WorkerFailure):
                map_sources(self.db, self.inputs)
        runner.assert_not_called()
        self.assertEqual(self.db.execute('SELECT count(*) FROM wiki_runs').fetchone()[0], 1)
        self.assertEqual(self.db.execute('SELECT attempts FROM wiki_sources').fetchone()[0], 1)

    def test_organizer_rate_limit_preserves_log_and_blocks_following_attempt(self):
        self.check_cooldown('organize')

    def test_reviewer_rate_limit_preserves_log_and_blocks_following_attempt(self):
        self.check_cooldown('organize_review')
