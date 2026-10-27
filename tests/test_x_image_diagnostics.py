from x_trace_fixtures import IMAGE, SESSION, rollout, trace_fixture
import unittest

from x_curator.model_trace import pack
from x_curator.storage import sha256
from x_curator.worker_prompts import prompt


class ImageDiagnosticsTests(unittest.TestCase):
    def test_missing_and_changed_images_report_counts_index_and_digests(self):
        request, events, rows = trace_fixture()
        rows[1]['payload']['content'].pop()
        with self.assertRaisesRegex(ValueError, 'counts=0/1; index=0; actual=missing; expected=' + sha256(IMAGE)):
            pack(request, prompt(request), [], events, rollout(rows))
        request, events, rows = trace_fixture()
        rows[1]['payload']['content'][1]['image_url'] = 'data:image/png;base64,Y2hhbmdlZA=='
        with self.assertRaisesRegex(ValueError, 'actual=' + sha256(b'changed') + '; expected=' + sha256(IMAGE)):
            pack(request, prompt(request), [], events, rollout(rows))

    def test_prompt_mismatch_retains_the_original_exact_match_count(self):
        request, events, rows = trace_fixture()
        rows[1]['payload']['content'][0]['text'] = 'different prompt'
        with self.assertRaisesRegex(ValueError, 'exactly once; matches=0'):
            pack(request, prompt(request), [], events, rollout(rows))
