import json
from unittest.mock import patch

from x_wiki_fixtures import WikiCase
from x_curator.wiki import run
from x_curator.wiki_current import current
from x_curator.wiki_keys import page_key
from x_curator.wiki_links import validate as validate_links


class WikiBuildTests(WikiCase):
    def test_real_build_has_backlinks_provenance_and_reuses_approved_mapping(self):
        with patch('x_curator.wiki_mapping.runner', return_value=self.model) as model:
            first = run(self.db, self.root)
            second = run(self.db, self.root)
        self.assertEqual(first, second)
        model.assert_called_once()
        self.assertEqual(first['mapped_sources'], 1)
        with patch('x_curator.wiki_files.wiki_links.validate', wraps=validate_links) as verifier:
            manifest = current(self.db, self.root)
        verifier.assert_not_called()
        folder = self.root / 'wiki/builds' / manifest['generation']
        topic = page_key(self.mapping['pages'][0])
        self.assertIn('../sources/' + self.publication, (folder / 'docs' / (topic + '.md')).read_text())
        source = (folder / 'docs/sources' / (self.publication + '.md')).read_text()
        self.assertIn('../' + topic, source)
        self.assertIn(self.packet['bundle_sha'], source)
        self.assertGreater(validate_links(folder / 'site'), 2)
        mapping = json.loads((folder / 'docs/source-map.json').read_text())
        self.assertEqual(mapping[self.publication], [topic])

    def test_broken_rendered_link_preserves_source_fallback(self):
        with patch('x_curator.wiki_mapping.runner', return_value=self.model), patch(
                'x_curator.wiki_build.wiki_links.validate', side_effect=[None, ValueError('broken link')]):
            with self.assertRaisesRegex(ValueError, 'broken link'):
                run(self.db, self.root)
        self.assertIsNotNone(current(self.db, self.root))
        self.assertEqual(self.db.execute('SELECT state FROM wiki_runs').fetchone()[0], 'accepted')
        with patch('x_curator.wiki_mapping.runner') as model:
            self.assertEqual(run(self.db, self.root)['mapped_sources'], 1)
        model.assert_not_called()
