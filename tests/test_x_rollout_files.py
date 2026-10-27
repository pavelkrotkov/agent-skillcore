from pathlib import Path
import tempfile
import unittest

from x_trace_fixtures import SESSION, rollout, trace_fixture
from x_curator.model_rollout import read


class RolloutFilesTests(unittest.TestCase):
    def test_only_the_matching_persisted_session_can_supply_the_rollout(self):
        _, log, rows = trace_fixture()
        with tempfile.TemporaryDirectory() as directory:
            environment = {'CODEX_HOME': directory}
            with self.assertRaisesRegex(ValueError, 'unique persistent'):
                read(log, environment)
            sessions = Path(directory) / 'sessions'
            sessions.mkdir()
            (sessions / ('rollout-' + SESSION + '.jsonl')).write_bytes(rollout(rows))
            self.assertEqual(read(log, environment), rollout(rows))
            (sessions / ('duplicate-' + SESSION + '.jsonl')).write_bytes(rollout(rows))
            with self.assertRaisesRegex(ValueError, 'unique persistent'):
                read(log, environment)
