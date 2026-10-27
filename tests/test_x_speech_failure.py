import subprocess
import json
from unittest.mock import patch

from x_publication_fixtures import PublicationCase
from x_curator.speech_execution import run


class SpeechFailureTests(PublicationCase):
    def test_timeout_retains_actual_partial_outputs_without_a_success_receipt(self):
        working = self.root / 'temporary'
        working.mkdir()
        (working / 'result.json').write_bytes(b'{partial real reader output')
        error = subprocess.TimeoutExpired('reader', 540, output=b'partial stdout', stderr=b'actual reader diagnostic')
        with patch('x_curator.speech_execution.subprocess.run', side_effect=error):
            with self.assertRaises(subprocess.TimeoutExpired):
                run(['reader'], working, self.root, 'speech/synthetic')
        output = self.root / 'speech/synthetic'
        self.assertEqual({p.read_bytes() for p in output.iterdir() if not p.name.startswith('failure-')},
                         {b'{partial real reader output', b'partial stdout', b'actual reader diagnostic'})
        self.assertFalse(list(output.glob('receipt-*')))
        self.assertEqual(json.loads(next(output.glob('failure-*')).read_text())['state'], 'failed')
