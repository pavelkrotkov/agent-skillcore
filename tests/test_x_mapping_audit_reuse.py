from copy import deepcopy
from unittest.mock import patch

from x_wiki_fixtures import WikiCase
from x_curator import wiki_inputs, wiki_mapping_receipts
from x_curator.wiki_mapping import map_sources


class MappingAuditReuseTests(WikiCase):
    def accepted(self):
        with patch('x_curator.wiki_mapping.runner', return_value=self.model):
            return map_sources(self.db, self.inputs)

    def test_mapping_proof_reuses_receipts_without_sharing_mutable_outputs(self):
        self.accepted()
        with patch.object(wiki_mapping_receipts, 'verified', wraps=wiki_mapping_receipts.verified) as proof:
            pages = wiki_inputs.mappings(self.db, self.sources)
            expected = deepcopy(pages)
            next(iter(pages.values()))['claims'][0]['claim'] = 'Mutated caller output'
            self.assertEqual(wiki_inputs.mappings(self.db, self.sources), expected)
        self.assertEqual(proof.call_count, 1)

    def test_changed_mapping_review_cannot_reuse_accepted_proof(self):
        identity = self.accepted()
        wiki_inputs.mappings(self.db, self.sources)
        with self.db:
            self.db.execute('UPDATE wiki_runs SET review=? WHERE id=?', (b'{"type":"turn.failed"}', identity))
        with self.assertRaises(ValueError):
            wiki_inputs.mappings(self.db, self.sources)
