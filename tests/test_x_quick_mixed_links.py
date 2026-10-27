from unittest.mock import patch

from x_linked_fixtures import LinkedCase


class QuickMixedLinkTests(LinkedCase):
    def test_channel_link_does_not_block_a_readable_article(self):
        urls = ['https://example.test/release', 'https://www.youtube.com/@channel']
        with patch('x_curator.quick_linked.links', return_value=urls):
            result = self.run_worker()
        self.assertEqual(result['completed'], 1)
        self.assertFalse(self.validation['isError'])
