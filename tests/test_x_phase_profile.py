import json
from unittest.mock import patch
from x_quick_phase_fixtures import PhaseCase
from x_curator import codex_runner


class PhaseProfileTests(PhaseCase):
    def test_real_runner_always_exposes_the_bounded_evidence_phase(self):
        with patch('x_curator.codex_runner.shutil.which', return_value='codex'), \
                patch('x_curator.codex_runner.login_status'):
            executor = codex_runner.runner(self.db, self.token)
        self.assertTrue(callable(executor.evidence))

    def test_real_final_profile_has_no_search_or_read_and_keeps_the_original_model(self):
        self.assertIsNotNone(self.run_phases())
        row = self.db.execute("SELECT input FROM executions WHERE role='factcheck'").fetchone()
        root = self.root / 'runs' / self.token
        with patch('x_curator.codex_runner.attachments', return_value=[]):
            args = codex_runner.arguments(self.db, root, 'codex', json.loads(row['input']))
        settings = dict(args[i + 1].split('=', 1) for i, arg in enumerate(args) if arg == '-c')
        self.assertEqual(settings['web_search'], '"disabled"')
        self.assertEqual(json.loads(settings['mcp_servers.curator.enabled_tools']), ['validate'])
        self.assertEqual(args[args.index('--model') + 1], 'gpt-5.6-sol')
        self.assertEqual(settings['model_reasoning_effort'], '"high"')
        self.assertEqual(settings['forced_login_method'], '"chatgpt"')
        self.assertIn('--output-schema', args)
