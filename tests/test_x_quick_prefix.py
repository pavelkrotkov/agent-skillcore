import json
import time

from x_quick_fixtures import QuickCase
from x_curator import blobs, public_http, quick_mcp, quick_sources, quick_store


class QuickPrefixTests(QuickCase):
    def read(self, body):
        quick_store.start(self.db, self.token, time.time())
        identity = quick_sources.source(self.db, self.token, 'https://example.test/large')
        with self.transport(body) as response:
            result = quick_mcp.call(self.db, self.token, 'read', {'source': identity})
            response.read.assert_called_once_with(1_048_577)
        return result

    def test_large_html_retains_a_verifiable_prefix_and_explicit_partial_coverage(self):
        body = b'<p>The tool was released in 2025.</p>' + b'<script>' + b'x' * 2_097_152
        result = self.read(body)
        self.assertFalse(result['isError'], result)
        evidence = json.loads(result['content'][0]['text'])['evidence']
        self.assertEqual(evidence['text'], 'The tool was released in 2025.')
        self.assertTrue(evidence['truncated'])
        self.assertIn('first 1048576 bytes', ' '.join(evidence['limitations']))
        self.assertEqual(blobs.read(self.db, evidence['body_sha']), body[:1_048_577])
        self.assertEqual(self.db.execute('SELECT count(*) FROM retrievals').fetchone()[0], 1)
        self.assertEqual(quick_store.active(self.db, self.token)['searches'], 0)

    def test_script_only_prefix_does_not_invent_unread_body_content(self):
        body = b'<script>' + b'x' * 2_097_152 + b'</script><p>Unseen evidence.</p>'
        result = self.read(body)
        self.assertTrue(result['isError'])
        self.assertIn('too sparse', result['content'][0]['text'])

    def test_normal_complete_download_still_rejects_oversize(self):
        with self.transport(b'x' * 33):
            with self.assertRaisesRegex(ValueError, 'acquisition byte budget'):
                public_http.exchange('https://example.test/large', max_bytes=32)
