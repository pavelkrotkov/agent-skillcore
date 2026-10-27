"""Reused parsing facts never replace fresh target and anchor validation."""
from unittest.mock import patch
from x_fixtures import CollectionCase
from x_curator import wiki_links


class HTMLCacheTests(CollectionCase):
    def test_cached_html_still_checks_changed_targets_and_missing_assets(self):
        site=self.root/'site'
        site.mkdir()
        (site/'index.html').write_text('<a href="page.html#ok">page</a>')
        page=site/'page.html'
        page.write_text('<h1 id="ok">target</h1>')
        self.assertEqual(wiki_links.validate(site,self.root),2)
        with patch('x_curator.wiki_html_cache.Links.feed',side_effect=AssertionError('reparsed unchanged HTML')):
            self.assertEqual(wiki_links.validate(site,self.root),2)
        page.write_text('<h1 id="changed">target</h1>')
        with self.assertRaisesRegex(ValueError,'anchor'):
            wiki_links.validate(site,self.root)
        page.unlink()
        with self.assertRaisesRegex(ValueError,'missing'):
            wiki_links.validate(site,self.root)
