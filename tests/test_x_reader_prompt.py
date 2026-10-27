import json
import time
import unittest
from unittest.mock import patch

from x_quick_fixtures import QuickCase
from x_curator import deep_prompt, quick_prompt, quick_sources, quick_store, quick_mcp


class ReaderExcerptTests(QuickCase):
    def test_large_unicode_read_preserves_match_offsets_and_compact_transport(self):
        quick_store.start(self.db, self.token, time.time())
        source = quick_sources.source(self.db, self.token, 'https://example.test/start')
        body = ('🧠' * 8000 + 'Target passage.' + '🧠' * 8000).encode()
        with patch('x_curator.quick_web.fetch', return_value=(200, 'text/plain', body, None)):
            result = quick_mcp.call(self.db, self.token, 'read', {'source': source, 'match': 'Target passage.'})
        text = result['content'][0]['text']
        evidence = json.loads(text)['evidence']
        self.assertEqual(evidence['excerpt_start'], 6000)
        self.assertEqual(evidence['text'], body.decode()[6000:12000])
        self.assertIn('Target passage.', evidence['text'])
        self.assertLess(len(text.encode()), 32000)


class ReaderPromptTests(unittest.TestCase):
    def test_quick_and_deep_routes_share_complete_single_read_transport(self):
        for prompt in (quick_prompt.NATIVE, deep_prompt.instructions()):
            with self.subTest(prompt=prompt[:40]):
                self.assertIn(quick_prompt.READ_OUTPUT, prompt)
                self.assertIn('max_output_tokens:16000', prompt)
                self.assertIn('Do not batch reads', prompt)
                self.assertIn('partial resource coverage, not lost tool output', prompt)
                self.assertIn('Missing or truncated tool output cannot', prompt)
                self.assertIn('If a claim needs unseen context, return inconclusive', prompt)
        self.assertIn('TWELVE targeted searches', deep_prompt.instructions())
        self.assertNotIn('120 seconds total', deep_prompt.instructions())
