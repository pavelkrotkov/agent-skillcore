import json
import subprocess
from unittest.mock import patch

from x_wiki_fixtures import WikiCase
from x_curator import provider_health
from x_curator.codex_runner import runner
from x_curator.wiki_mapping import map_sources
from x_curator.worker_errors import WorkerFailure
from x_curator.supervisor import run
from x_curator.command_lock import lockfile
from x_curator.accounting import report


class SupervisionRegressionTests(WikiCase):
    def test_preflight_failures_pause_repeated_wiki_reservations(self):
        with patch('x_curator.wiki_mapping.runner', side_effect=WorkerFailure('login unavailable', b'')):
            for _ in range(2):
                with self.assertRaises(WorkerFailure):
                    map_sources(self.db, self.inputs)
        self.assertIsNotNone(provider_health.blocked(self.db))
        self.assertEqual(self.db.execute('SELECT attempts FROM wiki_sources').fetchone()[0], 1)
        with patch('x_curator.codex_runner.shutil.which', return_value='codex'), patch('x_curator.codex_profile.subprocess.run', side_effect=subprocess.TimeoutExpired('codex', 15)):
            with self.assertRaises(WorkerFailure):
                runner(self.db, self.token)

    def test_cycle_reports_are_bounded_and_wiki_invalidation_is_locked(self):
        with patch('x_curator.supervisor.phases'):
            for _ in range(10):
                result = run(self.db, self.root, None, 0, 0, 30)
        self.assertLess(len(json.dumps(result)), 10000)
        cycles = result['report']['operations']['cycles']
        self.assertNotIn('result', cycles[0])
        with lockfile(self.root, '.wiki.lock'):
            with self.assertRaises(BlockingIOError):
                report(self.db, self.root)
