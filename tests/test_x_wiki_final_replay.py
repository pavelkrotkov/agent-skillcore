from unittest.mock import patch

from x_wiki_fixtures import WikiCase
from x_wiki_final_fixtures import compact
from x_curator import wiki, wiki_draft
from x_curator.wiki_mapping import map_sources
from x_curator.wiki_mapping_receipts import verified
from x_curator.wiki_prompt_payload import payload


class WikiFinalReplayTests(WikiCase):
    reject = False

    def model(self, request):
        if request['role'] == 'organize':
            identity = self.db.execute("SELECT id FROM wiki_runs WHERE state='running'").fetchone()[0]
            packet = payload(dict(request, proposal=self.mapping))['proposal']
            response = wiki_draft.call(self.db, identity, 'validate', dict(proposal=packet))
            self.assertFalse(response['isError'])
            return compact(request, packet, response)
        self.assertEqual(request['proposal'], self.mapping)
        return self.feedback_response(request, ['Synthetic editorial rejection.'] if self.reject else None)

    def test_compact_final_maps_builds_and_replays_the_exact_independently_reviewed_draft(self):
        with patch('x_curator.wiki_mapping.runner', return_value=self.model):
            identity = map_sources(self.db, self.inputs)
        row = dict(self.db.execute('SELECT * FROM wiki_runs WHERE id=?', (identity,)).fetchone())
        self.assertEqual(verified(row)[1], self.mapping)
        self.assertEqual(row['expires'] - row['started'], 600)
        self.assertEqual(self.db.execute('SELECT attempts FROM wiki_sources').fetchone()[0], 1)
        result = wiki.run(self.db, self.root, 0)
        self.assertEqual((result['mapped_sources'], result['unmapped_sources']), (1, 0))

    def test_successful_validation_and_compact_final_do_not_override_independent_rejection(self):
        self.reject = True
        with patch('x_curator.wiki_mapping.runner', return_value=self.model):
            with self.assertRaisesRegex(ValueError, 'independent approval'):
                map_sources(self.db, self.inputs)
        self.assertEqual(self.db.execute('SELECT state FROM wiki_runs').fetchone()[0], 'failed')
        self.assertFalse((self.root / 'wiki/CURRENT.json').exists())
