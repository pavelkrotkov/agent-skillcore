import json
import time
from unittest.mock import patch

from x_quick_fixtures import QuickCase
from x_curator import quick_mcp, quick_store


class QuickSearchResultsTests(QuickCase):
    def test_blocked_result_does_not_discard_primary_product_results(self):
        quick_store.start(self.db, self.token, time.time())
        hosts = ['www.google.com', 'workspace.google.com', 'support.google.com', 'sites.google.com', 'play.google.com']
        items = ''.join(f'<item><title>{host}</title><link>https://{host}/source</link></item>' for host in hosts)
        body = ('<rss><channel>' + items + '</channel></rss>').encode()
        with patch('x_curator.quick_search.fetch', return_value=(200, 'text/xml', body, None)) as fetch:
            result = quick_mcp.call(self.db, self.token, 'search', {'query': 'synthetic products'})
        self.assertFalse(result['isError'])
        self.assertEqual([item['title'] for item in json.loads(result['content'][0]['text'])], hosts[1:])
        self.assertEqual(fetch.call_count, 1)
        self.assertEqual(quick_store.active(self.db, self.token)['searches'], 1)
