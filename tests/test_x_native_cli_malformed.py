"""Exercise malformed native stdout through the actual CLI runner functions."""
from unittest.mock import patch

from x_native_search_fixtures import NativeCase
from x_curator import codex_runner, provider_health, quick_process, quick_profile


class NativeCLIMalformedTests(NativeCase):
    def cli_failure(self, evidence=False, status=0):
        log = self.search_log + b'not a model receipt\n'
        paths = []
        def execute(_args, _content, request, **kwargs):
            self.assertEqual(request['search_mode'], self.search_mode)
            kwargs['stdout'].write(log)
            paths.append(kwargs['output'])
            return status
        def runner(db, token):
            root = self.root / 'runs' / token
            root.mkdir(parents=True)
            if evidence:
                return quick_profile.checker(db, root, 'synthetic-codex', {})
            return lambda request: codex_runner.run(db, root, 'synthetic-codex', {}, request)
        with patch('x_curator.quick_process.runner', runner), \
                patch('x_curator.codex_runner.execute', execute), patch('x_curator.quick_phase_runner.execute', execute):
            quick_process.research(self.db, self.root, self.client, self.token)
        self.assertEqual(paths[0].read_bytes(), log)
        execution = self.db.execute('SELECT log,finished FROM executions').fetchone()
        check = self.db.execute('SELECT searches,outcome,reason FROM quick_checks').fetchone()
        self.assertEqual(tuple(execution), (log, None))
        self.assertEqual((check['searches'], check['outcome']), (4, 'inconclusive'))
        self.assertEqual(self.db.execute('SELECT state FROM jobs').fetchone()[0], 'retry')
        self.assertEqual(bool(provider_health.blocked(self.db)), bool(status))
        self.assertIn('WorkerFailure' if status else 'ModelCompletionError', check['reason'])

    def test_zero_exit_malformed_stdout_is_typed_before_final_rollout_packing(self):
        self.cli_failure()

    def test_zero_exit_malformed_evidence_stdout_is_typed_before_input_packing(self):
        self.cli_failure(evidence=True)

    def test_usage_parse_failure_cannot_replace_an_original_provider_error(self):
        self.cli_failure(status=1)

    def test_evidence_usage_parse_failure_cannot_replace_an_original_provider_error(self):
        self.cli_failure(evidence=True, status=1)
