import json
from types import SimpleNamespace
from unittest.mock import patch

from x_zk_fixtures import ZKCase
from x_curator import wiki_refresh
from x_curator.wiki_links import validate


class ZKBuildTests(ZKCase):
    def test_reviewed_slice_consolidates_notes_and_preserves_urls_provenance_and_future_reuse(self):
        previous, concept, peer = self.retained_pair()
        before = list(self.db.execute('SELECT publication,attempts FROM wiki_sources ORDER BY publication'))
        args = SimpleNamespace(state=self.root, publication=list(self.sources), page=list(previous), reason='Synthetic ZK slice')
        with patch('x_curator.wiki_mapping.runner', return_value=self.feedback_response):
            result = wiki_refresh.command(self.db, args)
        folder = self.root / 'wiki/builds' / result['generation']
        self.assertGreater(validate(folder / 'site'), 4)
        self.assertEqual(before, list(self.db.execute('SELECT publication,attempts FROM wiki_sources ORDER BY publication')))
        self.check_documents(folder, previous, concept, peer)

    def check_documents(self, folder, previous, concept, peer):
        note = (folder / 'docs' / (concept + '.md')).read_text()
        self.assertIn('## The idea', note)
        self.assertLess(note.index('## The idea'), note.index('## Supporting likes'))
        self.assertIn('../' + peer + '.md', note)
        mapping = json.loads((folder / 'docs/source-map.json').read_text())
        self.assertTrue(all(concept in keys for keys in mapping.values()))
        for old in previous:
            self.assertIn(concept + '.md', (folder / 'docs' / (old + '.md')).read_text())
