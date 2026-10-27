from copy import deepcopy
from unittest.mock import patch

from x_wiki_fixtures import WikiCase
from x_curator.receipts import encoded
from x_curator.wiki_mapping import map_sources
from x_curator.wiki_prompts import LIMIT, PROPOSAL_LIMIT, preflight, prompt, request
from x_publication_fixtures import events


class WikiCapacityTests(WikiCase):
    def test_complete_review_headroom_is_checked_before_reservation(self):
        self.inputs['padding'] = ''
        size = len(prompt(request('organize_review', self.inputs)))
        self.inputs['padding'] = 'x' * (LIMIT - PROPOSAL_LIMIT - size)
        preflight(self.inputs)
        self.inputs['padding'] += 'x'
        with patch('x_curator.wiki_mapping.runner') as call:
            with self.assertRaisesRegex(ValueError, 'headroom'):
                map_sources(self.db, self.inputs)
        call.assert_not_called()
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM wiki_sources').fetchone()[0], 0)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM wiki_runs').fetchone()[0], 0)

    def test_oversized_actual_proposal_consumes_only_its_author_attempt(self):
        packet = deepcopy(self.mapping)
        packet['pages'][0]['description'] = 'x' * PROPOSAL_LIMIT
        self.assertGreater(len(encoded(packet)), PROPOSAL_LIMIT)
        with patch('x_curator.wiki_mapping.runner', return_value=lambda _: events(packet)):
            with self.assertRaisesRegex(ValueError, 'reserved review allowance'):
                map_sources(self.db, self.inputs)
        row = self.db.execute('SELECT * FROM wiki_runs').fetchone()
        self.assertEqual((row['state'], row['review'], row['expires'] - row['started']), ('failed', None, 600))
        self.assertEqual(self.db.execute('SELECT attempts FROM wiki_sources').fetchone()[0], 1)
