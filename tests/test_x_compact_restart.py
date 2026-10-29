"""Durable approvals are independent of the process that created them."""
from pathlib import Path
import os
import subprocess
import sys

from x_compact_fixtures import CompactCase
from x_curator import compact_history


class CompactRestartTests(CompactCase):
    def test_a_fresh_interpreter_verifies_without_memos_or_model_history(self):
        compact_history.run(self.db, self.root, apply=True)
        for path in (self.root / 'audit-memos').glob('*.memo'):
            path.unlink()
        folder = Path(__file__).resolve().parents[1]
        env = dict(os.environ, PYTHONPATH=str(folder / 'skills/x-curator/scripts'))
        result = subprocess.run([sys.executable, str(folder / 'tests/x_compact_restart.py'), str(self.root)],
                                env=env, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('fresh-process compact verification passed', result.stdout)
