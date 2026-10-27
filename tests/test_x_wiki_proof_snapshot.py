"""Real wiki entry points share proofs without trusting changed dependencies."""
from unittest.mock import patch

from x_wiki_fixtures import WikiCase
from x_curator import wiki_inputs
from x_curator.wiki import run
from x_curator.wiki_input_load import Snapshot


class WikiProofSnapshotTests(WikiCase):
    def setUp(self):
        super().setUp()
        with patch('x_curator.wiki_mapping.runner', return_value=self.model):
            self.report = run(self.db, self.root)

    def test_readback_reuses_bound_inputs_and_rejects_mutation(self):
        snapshot = Snapshot(self.db, self.root)
        with patch.object(wiki_inputs, 'sources') as sources:
            self.assertEqual(snapshot.current()['generation'], self.report['generation'])
        sources.assert_not_called()
        snapshot.values[0].clear()
        with self.assertRaisesRegex(ValueError, 'snapshot'):
            snapshot.current()

    def test_unchanged_activation_and_readback_reuse_transactional_epoch(self):
        snapshot=Snapshot(self.db,self.root)
        with patch.object(snapshot.reads,'verify',side_effect=AssertionError('repeated query fence')):
            self.assertEqual(snapshot.build()['generation'],self.report['generation'])
            self.assertEqual(snapshot.current()['generation'],self.report['generation'])
