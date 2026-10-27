from unittest.mock import patch

from x_wiki_fixtures import WikiCase, events
from x_curator.wiki import run
from x_curator.wiki_current import current
from x_curator.receipts import digest
from x_curator import provider_health
from x_curator.deadlines import DeadlineExceeded


class WikiRecoveryTests(WikiCase):
    def test_oversized_base_input_still_builds_without_spending_mapping_attempts(self):
        with patch('x_curator.wiki_prompts.LIMIT', 100), patch('x_curator.wiki_mapping.runner') as model:
            result = run(self.db, self.root)
        model.assert_not_called()
        self.assertEqual(self.db.execute('SELECT count(*) FROM wiki_runs').fetchone()[0], 0)
        self.assertEqual(self.db.execute('SELECT count(*) FROM wiki_sources').fetchone()[0], 0)
        self.assertEqual((result['state'], result['mapped_sources'], result['unmapped_sources']), ('blocked', 0, 1))
        self.assertIn('envelope', result['action'])
        self.assertEqual(current(self.db, self.root)['generation'], result['generation'])

    def reject(self, request):
        if request['role'] == 'organize':
            return events(self.mapping)
        return events({'verdict': 'reject', 'input_sha': digest(self.inputs),
                       'proposal_sha': digest(self.mapping), 'findings': ['unsupported grouping']})

    def test_rejected_mapping_still_builds_verified_unmapped_sources(self):
        with patch('x_curator.wiki_mapping.runner', return_value=self.reject):
            result = run(self.db, self.root)
        self.assertEqual((result['state'], result['mapped_sources'], result['unmapped_sources']), ('blocked', 0, 1))
        self.assertIn('independent approval', result['action'])
        self.assertEqual(current(self.db, self.root)['generation'], result['generation'])
        self.assertEqual(self.db.execute('SELECT state FROM wiki_runs').fetchone()[0], 'failed')

    def test_provider_cooldown_rebuilds_without_spending_mapping_attempts(self):
        provider_health.suspend(self.db, 'synthetic outage')
        with patch('x_curator.wiki_mapping.runner') as model:
            result = run(self.db, self.root)
        model.assert_not_called()
        self.assertEqual(self.db.execute('SELECT count(*) FROM wiki_runs').fetchone()[0], 0)
        self.assertEqual(result['state'], 'blocked')
        self.assertIsNotNone(current(self.db, self.root))
        (self.root / 'wiki/builds' / result['generation'] / 'site/index.html').write_text('corrupt')
        with self.assertRaisesRegex(ValueError, 'readback'):
            run(self.db, self.root)
        self.assertIsNone(current(self.db, self.root))

    def test_mapping_deadline_preserves_verified_source_index(self):
        with patch('x_curator.wiki_mapping.map_sources', side_effect=DeadlineExceeded('expired')):
            with self.assertRaises(DeadlineExceeded):
                run(self.db, self.root)
        self.assertIsNotNone(current(self.db, self.root))
