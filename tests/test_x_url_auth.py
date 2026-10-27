from unittest.mock import Mock, patch
import unittest

from x_fixtures import SCRIPTS
from x_curator.x_urls import source_fetcher


class URLAuthTests(unittest.TestCase):
    def test_tracking_links_use_fixed_detail_route_and_lookalikes_never_receive_auth(self):
        client = Mock()
        client.detail.return_value = (200, b'synthetic')
        fetch = source_fetcher(client)
        with patch('x_curator.x_urls.public_http.fetch', return_value=(200, 'text/plain', b'public', None)) as public:
            fetch('https://www.x.com/author/status/123/?s=20#tracking')
            client.detail.assert_called_once_with('123')
            public.assert_not_called()
            fetch('https://x.com@other.example/author/status/123')
            fetch('https://x.com.other.example/author/status/123')
            self.assertEqual(public.call_count, 2)
            client.detail.assert_called_once()
