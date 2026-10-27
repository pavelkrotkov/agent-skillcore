import time
from unittest.mock import patch

from x_wiki_draft_fixtures import WikiDraftCase
from x_curator import wiki_draft, wiki_store
from x_curator.wiki import run
from x_curator.wiki_current import current


class WikiDraftTests(WikiDraftCase):
    def test_links_can_be_corrected_in_same_execution_before_review_and_activation(self):
        with patch('x_curator.wiki_mapping.runner', return_value=self.draft_model) as runner:
            result = run(self.db, self.root)
        runner.assert_called_once()
        self.assertEqual(result['mapped_sources'], 1)
        row = dict(self.db.execute('SELECT * FROM wiki_runs').fetchone())
        self.assertEqual(row['state'], 'accepted')
        self.assertEqual(row['expires'] - row['started'], 600)
        self.assertEqual(self.db.execute('SELECT attempts FROM wiki_sources').fetchone()[0], 1)
        self.assertNotEqual((self.root / 'wiki/CURRENT.json').read_bytes(), self.previous)
        self.assertEqual(current(self.db, self.root)['generation'], result['generation'])

    def test_passing_draft_does_not_allow_invalid_final_to_replace_current(self):
        self.corrected = False
        with patch('x_curator.wiki_mapping.runner', return_value=self.draft_model):
            result = run(self.db, self.root)
        self.assertEqual(result['state'], 'blocked')
        self.assertIn('missing-target', result['action'])
        self.assertEqual((self.root / 'wiki/CURRENT.json').read_bytes(), self.previous)
        row = dict(self.db.execute('SELECT * FROM wiki_runs').fetchone())
        self.assertEqual(row['state'], 'failed')
        self.assertIn('missing-target', row['action'])
        self.assertIsNone(row['review'])

    def test_expired_run_and_other_tools_cannot_validate_or_extend_allowances(self):
        identity = wiki_store.reserve(self.db, self.inputs)
        self.assertTrue(wiki_draft.call(self.db, identity, 'search', {})['isError'])
        with self.db:
            self.db.execute('UPDATE wiki_runs SET expires=?', (time.time() - 1,))
        before = '\n'.join(self.db.iterdump())
        with patch('x_curator.wiki_draft.validate', side_effect=AssertionError('must not validate')):
            self.assertTrue(wiki_draft.call(self.db, identity, 'validate', {'proposal': self.mapping})['isError'])
        self.assertEqual('\n'.join(self.db.iterdump()), before)
