from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from x_curator.wiki_links import resolve_target, validate


class WikiLinkTests(unittest.TestCase):
    def test_valid_links_are_deduplicated_only_within_one_validation(self):
        with TemporaryDirectory() as folder:
            site = Path(folder)
            link = '<a href="/page.html#ok">root</a><a href="page.html">relative</a>'
            (site / 'index.html').write_text(link)
            (site / 'other.html').write_text(link)
            (site / 'page.html').write_text('<h1 id="ok">ok</h1>')
            with patch('x_curator.wiki_links.resolve_target', wraps=resolve_target) as resolver:
                self.assertEqual(validate(site), 3)
            self.assertEqual(resolver.call_count, 2)
            (site / 'page.html').unlink()
            with self.assertRaisesRegex(ValueError, 'missing'):
                validate(site)

    def test_missing_anchor_file_and_root_escape_are_rejected(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            site = root / 'site'
            site.mkdir()
            (site / 'page.html').write_text('<h1 id="ok">ok</h1>')
            index = site / 'index.html'
            index.write_text('<a href="page.html#missing">anchor</a>')
            with self.assertRaisesRegex(ValueError, 'anchor'):
                validate(site)
            index.write_text('<a href="missing.html">missing</a>')
            with self.assertRaisesRegex(ValueError, 'missing'):
                validate(site)
            outside = root / 'outside.html'
            outside.write_text('outside')
            (site / 'escape.html').symlink_to(outside)
            index.write_text('<a href="escape.html">escape</a>')
            with self.assertRaisesRegex(ValueError, 'missing'):
                validate(site)


if __name__ == '__main__':
    unittest.main()
