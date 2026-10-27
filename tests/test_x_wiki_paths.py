from unittest.mock import patch

from x_wiki_fixtures import WikiCase
from x_curator.wiki_site import render_site
from x_curator.wiki_files import file_manifest


class WikiPathTests(WikiCase):
    def test_symlinked_output_cannot_overwrite_or_leak_into_git(self):
        folder = self.root / 'wiki/builds/synthetic'
        folder.mkdir(parents=True)
        checkout = self.root / 'unrelated'
        (checkout / '.git').mkdir(parents=True)
        sentinel = checkout / 'keep.txt'
        sentinel.write_text('preserve unrelated work')
        (folder / 'site').symlink_to(checkout, target_is_directory=True)
        with patch('x_curator.wiki_site.subprocess.run') as compiler:
            with self.assertRaisesRegex(ValueError, 'symlink or Git'):
                render_site(self.root, 'wiki/builds/synthetic')
        compiler.assert_not_called()
        self.assertEqual(sentinel.read_text(), 'preserve unrelated work')
        self.assertEqual(sorted(p.name for p in checkout.iterdir()), ['.git', 'keep.txt'])

    def test_nested_output_symlink_is_rejected_before_compiler_cleanup(self):
        site = self.root / 'wiki/builds/synthetic/site'
        site.mkdir(parents=True)
        (site / 'assets').symlink_to(self.root, target_is_directory=True)
        with patch('x_curator.wiki_site.subprocess.run') as compiler:
            with self.assertRaisesRegex(ValueError, 'symlink or Git'):
                render_site(self.root, 'wiki/builds/synthetic')
        compiler.assert_not_called()

    def test_manifest_requires_actual_rendered_index(self):
        with self.assertRaisesRegex(ValueError, 'index missing'):
            file_manifest(self.root, 'wiki/builds/missing', 'missing', {}, {})
