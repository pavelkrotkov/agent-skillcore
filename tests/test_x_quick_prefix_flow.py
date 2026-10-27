import json
from unittest.mock import patch

from x_quick_fixtures import QuickCase
from x_curator import quick_process
from x_curator.publication_audit import audit
from x_curator.wiki_sources import sources


class QuickPrefixFlowTests(QuickCase):
    def test_complete_tool_output_with_partial_resource_can_publish_and_replay(self):
        fetch = self.fetch
        def prefix(url):
            if 'format=rss' in url:
                return fetch(url)
            body = b'<p>The tool was released in 2025.</p><script>' + b'x' * 2_097_152
            return 200, 'text/html', body, None
        with patch('x_curator.quick_web.fetch', prefix), patch('x_curator.quick_search.fetch', prefix), \
                patch('x_curator.quick_process.runner', return_value=self.checker):
            identity = quick_process.research(self.db, self.root, self.client, self.token)
        self.assertIsNotNone(identity)
        row = self.db.execute("SELECT output FROM quick_tools WHERE name='read'").fetchone()
        self.assertIsNotNone(row, 'The supporting reader response must be retained')
        output = row[0]
        evidence = json.loads(json.loads(output)['content'][0]['text'])['evidence']
        self.assertTrue(evidence['truncated'])
        self.assertIn('first 1048576 bytes', ' '.join(evidence['limitations']))
        self.assertEqual(audit(self.db, self.root), [])
        self.assertEqual(set(sources(self.db, self.root)), {identity})
