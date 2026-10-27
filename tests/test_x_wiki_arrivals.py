import sqlite3
from unittest.mock import patch

from x_wiki_fixtures import WikiCase
from x_wiki_arrival_fixtures import publish_arrival
from x_curator import wiki_inputs
from x_curator.wiki import run
from x_curator.wiki_current import current


class WikiArrivalTests(WikiCase):
    def build(self):
        with patch('x_curator.wiki_mapping.runner', return_value=self.model):
            return run(self.db, self.root)

    def test_arrival_preserves_current_with_default_and_larger_audited_inputs(self):
        report = self.build()
        publish_arrival(self.db, self.root)
        sources = wiki_inputs.sources(self.db, self.root)
        pages = wiki_inputs.mappings(self.db, sources)
        self.assertEqual(len(sources), 2)
        self.assertEqual(wiki_inputs.sources(self.db, self.root, []), {})
        self.assertEqual(current(self.db, self.root)['generation'], report['generation'])
        self.assertEqual(current(self.db, self.root, sources, pages)['generation'], report['generation'])

    def test_corrupt_unincorporated_arrival_does_not_withdraw_valid_generation(self):
        report = self.build()
        arrival = publish_arrival(self.db, self.root)
        path = self.db.execute('SELECT path FROM publications WHERE id=?', (arrival,)).fetchone()[0]
        (self.root / path).write_text('tampered')
        with self.assertRaisesRegex(ValueError, 'verified evidence'):
            run(self.db, self.root)
        self.assertEqual(current(self.db, self.root)['generation'], report['generation'])

    def test_genuine_publication_during_build_does_not_change_snapshot_dependencies(self):
        original = wiki_inputs.sources
        other = sqlite3.connect(self.root / 'curator.sqlite3', timeout=0.05)
        other.row_factory = sqlite3.Row
        published = False
        def sources(db, root, publications=None):
            nonlocal published
            value = original(db, root, publications)
            if self.db.in_transaction and not published:
                published = True
                publish_arrival(other, root)
            return value
        try:
            with patch.object(wiki_inputs, 'sources', side_effect=sources):
                report = self.build()
        finally:
            other.close()
        self.assertEqual(report['verified_sources'], 2)
        self.assertEqual(len(wiki_inputs.sources(self.db, self.root)), 2)
        self.assertEqual(current(self.db, self.root)['generation'], report['generation'])
