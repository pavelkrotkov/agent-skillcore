from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from threading import Barrier

from x_publication_fixtures import PublicationCase
from x_provider_fixtures import recovery_proof
from x_curator import provider_health as health
from x_curator.codex_runner import runner
from x_curator.codex_profile import command
from x_curator.provider_recovery import recover
from x_curator.storage import open_store


class ProviderObserverTests(PublicationCase):
    def test_concurrent_connections_journal_and_release_exactly_once(self):
        with patch('time.time', return_value=100):
            health.suspend(self.db, 'failure')
        failure = health.current(self.db)
        request = {'role': 'research', 'bundle': self.evidence, 'proposal': None}
        log = recovery_proof(request, 102)
        barrier = Barrier(2)
        def attempt(_):
            with closing(open_store(self.root)) as db:
                barrier.wait(timeout=5)
                return recover(db, failure, 101, request, log, command('codex', False) + ['-'])
        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(sorted(pool.map(attempt, range(2))), [False, True])
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM provider_recoveries').fetchone()[0], 1)

    def test_each_invocation_observes_failure_and_preserves_newer_failure(self):
        request = {'role': 'research', 'bundle': self.evidence, 'proposal': None}
        with patch('x_curator.codex_runner.shutil.which', return_value='codex'), patch('x_curator.codex_runner.login_status'):
            call = runner(self.db, self.token)
        with patch('time.time', return_value=100):
            health.suspend(self.db, 'failure after runner creation')
        with patch('time.time', return_value=101), patch('x_curator.codex_runner.run', return_value=recovery_proof(request, 101)):
            call(request)
        self.assertIsNone(health.current(self.db))
        with patch('time.time', return_value=102):
            health.suspend(self.db, 'next failure')
        def concurrent_failure(*_):
            health.suspend(self.db, 'newer failure during model execution')
            return recovery_proof(request, 103)
        with patch('time.time', return_value=103), patch('x_curator.codex_runner.run', side_effect=concurrent_failure):
            call(request)
        self.assertEqual(health.current(self.db)['action'], 'newer failure during model execution')
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM provider_recoveries').fetchone()[0], 1)
