"""Malformed completions retry; rejected approval proofs remain held."""
import json
from unittest.mock import patch

from x_retry_fixtures import RetryCase
from x_curator import provider_health, quick_process, quick_store
from x_curator.receipts import encoded


class CompletionRetryTests(RetryCase):
    def completion_failure(self, log):
        with patch('x_curator.quick_process.runner', return_value=lambda _: log):
            quick_process.research(self.db, self.root, self.client, self.token)
        old = dict(self.db.execute('SELECT * FROM quick_checks').fetchone())
        execution = dict(self.db.execute('SELECT * FROM executions').fetchone())
        self.assertEqual(self.db.execute('SELECT state FROM jobs').fetchone()[0], 'retry')
        self.assertEqual((execution['log'], execution['finished']), (log, None))
        self.assertIsNone(provider_health.blocked(self.db))
        self.next_attempt()
        child = quick_store.start(self.db, self.token, old['deadline'] + 1)
        self.assertNotEqual(child['id'], old['id'])
        self.assertEqual(dict(self.db.execute('SELECT * FROM quick_checks WHERE id=?', (old['id'],)).fetchone()), old)
        self.assertEqual(self.db.execute('SELECT log FROM executions WHERE id=?', (execution['id'],)).fetchone()[0], log)

    def test_missing_turn_completion_retries_at_the_actual_recorded_execution_boundary(self):
        self.completion_failure(encoded({'type': 'thread.started', 'thread_id': 'synthetic-session'}) + b'\n')

    def test_malformed_native_stream_retries_without_discarding_original_bytes(self):
        self.completion_failure(b'not a model receipt')

    def test_invalid_final_json_retries_without_a_substantive_factual_verdict(self):
        events = [{'type': 'thread.started', 'thread_id': 'synthetic-session'},
                  {'type': 'item.completed', 'item': {'type': 'agent_message', 'text': '{malformed'}},
                  {'type': 'turn.completed'}]
        self.completion_failure(b'\n'.join(encoded(event) for event in events))

    def test_rejected_rollout_session_is_not_a_completion_failure(self):
        original = self.checker
        def foreign_session(request):
            proof = json.loads(original(request))
            rows = [json.loads(line) for line in proof['rollout'].splitlines()]
            rows[0]['payload']['id'] = 'foreign-session'
            proof['rollout'] = '\n'.join(json.dumps(row) for row in rows)
            return encoded(proof)
        with patch('x_curator.quick_process.runner', return_value=foreign_session), \
                patch('x_curator.quick_search.fetch', self.fetch), patch('x_curator.quick_web.fetch', self.fetch):
            quick_process.research(self.db, self.root, self.client, self.token)
        self.assertEqual(self.db.execute('SELECT state FROM jobs').fetchone()[0], 'awaiting_review')
        self.assertEqual(self.db.execute('SELECT count(*) FROM quick_retry_failures').fetchone()[0], 0)
