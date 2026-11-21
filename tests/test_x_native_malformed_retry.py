"""Malformed native bytes retain truthful usage and allow a separate bounded retry."""
import json
from unittest.mock import patch

from x_native_retry_fixtures import NativeRetryCase
from x_curator import policy_timings, quick_process
from x_curator.receipts import encoded
from x_curator.storage import open_store


class NativeMalformedRetryTests(NativeRetryCase):
    def test_malformed_complete_line_seals_the_check_with_unknown_total_usage(self):
        check, _ = self.malformed(b'not a model receipt\n')
        metrics = policy_timings.measure(self.db, check, 'check', None)
        self.assertIsNone(metrics['searches'])
        self.assertFalse(metrics['search_usage_complete'])

    def test_valid_prefix_queries_survive_malformed_bytes_and_a_subsequent_retry(self):
        suffix = encoded({'type': 'item.completed', 'item': {'id': 'unknown-tail', 'type': 'web_search',
                         'action': {'type': 'search', 'query': 'untrusted remainder'}}}) + b'\n'
        log = self.search_log + b'not a model receipt\n' + suffix
        original_token = self.token
        check, execution = self.malformed(log)
        metrics = policy_timings.measure(self.db, check, 'check', None)
        self.assertEqual(check['searches'], 4)
        self.assertEqual(metrics['observed_searches_lower_bound'], 4)
        self.assertIsNone(metrics['searches'])
        self.assertFalse(metrics['search_usage_complete'])
        self.db.close()
        self.db = open_store(self.root)
        self.resume()
        self.assertIsNotNone(self.run_check())
        self.assertNotEqual(self.token, original_token)
        self.assertEqual(dict(self.db.execute('SELECT * FROM quick_checks WHERE id=?', (check['id'],)).fetchone()), check)
        self.assertEqual(self.db.execute('SELECT log FROM executions WHERE id=?', (execution['id'],)).fetchone()[0], log)

    def test_native_rollout_proof_rejection_stays_held_without_a_technical_retry(self):
        original = self.checker
        def malformed_rollout(request):
            proof = json.loads(original(request))
            proof['rollout'] = 'not a controller rollout\n'
            return encoded(proof)
        with patch('x_curator.quick_process.runner', return_value=malformed_rollout), \
                patch('x_curator.quick_web.fetch', self.fetch):
            quick_process.research(self.db, self.root, self.client, self.token)
        self.assertEqual(self.db.execute('SELECT state FROM jobs').fetchone()[0], 'awaiting_review')
        self.assertEqual(self.db.execute('SELECT count(*) FROM quick_retry_failures').fetchone()[0], 0)
