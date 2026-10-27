import unittest
from unittest.mock import patch

from x_curator.quick_articles import derive
from x_curator.x_urls import article_identity


class ArticleBoundaryTests(unittest.TestCase):
    def test_missing_identity_and_empty_or_invalid_windows_are_rejected(self):
        evidence = dict(captures=dict(parent=dict(kind='x_detail')))
        cases = [(dict(plain_text='Body.'), 'https://example.test/not-an-article', 0),
                 (dict(rest_id='1', plain_text='Body.'), 'https://x.com/i/article/1', 5),
                 (dict(rest_id='1', plain_text='Body.'), 'https://x.com/i/article/1', -1),
                 (dict(rest_id='1', plain_text='Body.'), 'https://x.com/i/article/1', True)]
        for article, url, start in cases:
            with self.subTest(article=article, url=url, start=start), \
                 patch('x_curator.quick_articles.retrieval'), \
                 patch('x_curator.quick_articles.entity', return_value=article):
                with self.assertRaises(ValueError):
                    derive(None, evidence, 'parent', url, start)

    def test_article_urls_share_exact_https_identity_with_optional_trailing_slash(self):
        for url in ('https://x.com/i/article/1', 'https://x.com/i/article/1/?utm_source=test'):
            self.assertEqual(article_identity(url), '1')
        for url in ('http://x.com/i/article/1', 'https://x.com.evil.test/i/article/1', '/i/article/1'):
            self.assertIsNone(article_identity(url))
