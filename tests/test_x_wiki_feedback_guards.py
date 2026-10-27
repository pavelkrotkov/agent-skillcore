from copy import deepcopy
import json
from unittest.mock import patch
from x_wiki_fixtures import WikiCase
from x_trace_fixtures import proof
from x_curator.receipts import digest, encoded
from x_curator.wiki_mapping import map_sources
from x_curator.wiki_mapping_feedback import previous_rejection


class WikiFeedbackGuardTests(WikiCase):
    def test_changed_inputs_tampered_request_and_unbound_verdict_do_not_feed_back(self):
        row = self.reject_mapping()
        changed = deepcopy(self.inputs)
        changed['catalog_sha'] = 'different'
        self.assertIsNone(previous_rejection(self.db, changed))
        log = json.loads(row['review'])
        log['request_sha'] = 'tampered'
        with self.db:
            self.db.execute('UPDATE wiki_runs SET review=? WHERE id=?', (encoded(log), row['id']))
        self.assertIsNone(previous_rejection(self.db, self.inputs))
        log = json.loads(row['review'])
        request = json.loads(log['prompt'].partition('\nUNTRUSTED INPUTS:\n')[2])
        request.pop('input_sha')
        request.pop('proposal_sha')
        verdict = dict(verdict='reject', input_sha=digest(self.inputs), proposal_sha='unbound', findings=['Problem.'])
        with self.db:
            self.db.execute('UPDATE wiki_runs SET review=? WHERE id=?', (proof(request, verdict), row['id']))
        self.assertIsNone(previous_rejection(self.db, self.inputs))

    def test_same_session_rejection_is_not_independent_feedback(self):
        with patch('x_curator.wiki_mapping.runner', return_value=lambda r: self.feedback_response(r, ['Problem.'], 'same-session')):
            with self.assertRaisesRegex(ValueError, 'separate session'):
                map_sources(self.db, self.inputs)
        self.assertIsNone(previous_rejection(self.db, self.inputs))

    def test_oversized_feedback_does_not_reserve_another_attempt(self):
        self.reject_mapping('x' * 1000000)
        with patch('x_curator.wiki_mapping.runner') as runner:
            with self.assertRaisesRegex(ValueError, 'model envelope|headroom'):
                map_sources(self.db, self.inputs)
        runner.assert_not_called()
        self.assertEqual(self.db.execute('SELECT attempts FROM wiki_sources').fetchone()[0], 1)

    def test_malformed_completed_review_is_ignored_on_next_ordinary_attempt(self):
        def malformed(request):
            return self.feedback_response(request) if request['role'] == 'organize' else proof(request, [])
        with patch('x_curator.wiki_mapping.runner', return_value=malformed):
            with self.assertRaisesRegex(ValueError, 'independent approval'):
                map_sources(self.db, self.inputs)
        self.assertIsNone(previous_rejection(self.db, self.inputs))
        with patch('x_curator.wiki_mapping.runner', return_value=self.feedback_response):
            map_sources(self.db, self.inputs)
        self.assertEqual(self.db.execute('SELECT attempts FROM wiki_sources').fetchone()[0], 2)
