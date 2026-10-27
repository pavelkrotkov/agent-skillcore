from unittest.mock import patch

from x_publication_fixtures import PublicationCase
from x_fixtures import Client
from x_curator.worker import process, work
from x_curator.worker_errors import WorkerFailure
from x_curator.packets import validate


class ProviderHealthTests(PublicationCase):
    def test_provider_outage_does_not_consume_following_source_attempts(self):
        job = dict(self.db.execute('SELECT * FROM jobs').fetchone())
        with patch('x_curator.worker_process.research', side_effect=WorkerFailure('quota unavailable', b'events')):
            self.assertEqual(process(self.db, self.root, None, job)['state'], 'provider_blocked')
        with self.db:
            self.db.execute('UPDATE jobs SET next_at=0')
        result = work(self.db, self.root, Client([]), 2)
        self.assertEqual((result['state'], result['attempted']), ('blocked', 0))
        self.assertEqual(self.db.execute('SELECT attempts FROM jobs').fetchone()[0], 1)

    def test_final_failure_reports_needs_action_and_preserves_model_reason(self):
        with self.db:
            self.db.execute('UPDATE jobs SET attempts=max_attempts')
        job = dict(self.db.execute('SELECT * FROM jobs').fetchone())
        with patch('x_curator.worker_process.research', side_effect=ValueError('inspect source')):
            self.assertEqual(process(self.db, self.root, None, job)['state'], 'needs_action')
        with self.assertRaisesRegex(ValueError, 'obtain the missing primary paper'):
            validate({'unresolved': 'obtain the missing primary paper'}, {})

    def test_selected_model_route_does_not_inherit_previous_model_cooldown(self):
        from x_curator import provider_health as health
        from x_curator.codex_profile import MODEL, command
        with patch.object(health, 'ROUTE', 'chatgpt-gpt-6.1-sol'):
            health.suspend(self.db, 'Previous model at capacity')
            previous = health.current(self.db)
        self.assertEqual(MODEL, 'gpt-5.6-sol')
        self.assertEqual(health.ROUTE, 'chatgpt-' + MODEL)
        self.assertIsNone(health.blocked(self.db))
        self.assertEqual(dict(self.db.execute('SELECT * FROM provider_health').fetchone()), previous)
        profile = command('codex', False)
        self.assertEqual(profile[profile.index('--model') + 1], MODEL)
        self.assertIn('model_reasoning_effort="high"', profile)
        self.assertIn('forced_login_method="chatgpt"', profile)
