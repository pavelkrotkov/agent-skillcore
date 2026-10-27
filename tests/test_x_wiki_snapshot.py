import json
from unittest.mock import patch

from x_wiki_fixtures import WikiCase
from x_curator import wiki_inputs
from x_curator.wiki import run
from x_curator.wiki_current import current


class WikiSnapshotTests(WikiCase):
    def build(self):
        with patch('x_curator.wiki_mapping.runner', return_value=self.model):
            return run(self.db, self.root)

    def test_unchanged_cycle_reuses_initial_audit_with_activation_fence(self):
        expected = self.build()
        with patch.object(wiki_inputs, 'sources', wraps=wiki_inputs.sources) as sources:
            with patch.object(wiki_inputs, 'mappings', wraps=wiki_inputs.mappings) as mappings:
                self.assertEqual(run(self.db, self.root), expected)
        sources.assert_not_called()
        mappings.assert_not_called()

    def test_empty_verified_snapshot_withdraws_without_falling_back_to_database(self):
        self.build()
        with patch.object(wiki_inputs, 'sources') as sources:
            with self.assertRaisesRegex(ValueError, 'stale'):
                current(self.db, self.root, {}, {})
        sources.assert_not_called()
        self.assertIsNone(current(self.db, self.root))

    def test_corrupt_source_withdraws_current_before_propagating_failure(self):
        self.build()
        row = self.db.execute('SELECT path FROM publications WHERE id=?', (self.publication,)).fetchone()
        (self.root / row['path']).write_text('tampered')
        with self.assertRaisesRegex(ValueError, 'verified evidence'):
            run(self.db, self.root)
        self.assertIsNone(json.loads((self.root / 'wiki/CURRENT.json').read_text())['generation'])
