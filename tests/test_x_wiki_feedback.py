from unittest.mock import patch

from x_wiki_fixtures import WikiCase
from x_curator.receipts import digest
from x_curator.wiki_mapping import map_sources
from x_curator.wiki_mapping_feedback import previous_rejection
from x_curator.wiki_mapping_receipts import verified


class WikiFeedbackTests(WikiCase):
    def test_authentic_rejection_reaches_next_proposal_and_final_audit(self):
        rejected = self.reject_mapping()
        feedback = previous_rejection(self.db, self.inputs)
        self.assertEqual(feedback['review'], rejected['id'])
        self.assertEqual(feedback['proposal'], self.mapping)
        requests = []

        def corrected(request):
            requests.append(request)
            return self.feedback_response(request)

        with patch('x_curator.wiki_mapping.runner', return_value=corrected):
            identity = map_sources(self.db, self.inputs)
        self.assertEqual(requests[0]['bundle']['wiki_inputs']['feedback'], feedback)
        inputs, packet = verified(self.db.execute('SELECT * FROM wiki_runs WHERE id=?', (identity,)).fetchone())
        self.assertEqual(inputs['feedback'], feedback)
        self.assertEqual(packet['input_sha'], digest(inputs))
        self.assertEqual(self.db.execute('SELECT attempts FROM wiki_sources').fetchone()[0], 2)

    def test_latest_feedback_advances_without_increasing_attempt_limit(self):
        self.reject_mapping('First unsupported title.')
        latest = self.reject_mapping('Second unsupported relationship.')
        feedback = previous_rejection(self.db, self.inputs)
        self.assertEqual(feedback['review'], latest['id'])
        self.assertEqual(feedback['findings'], ['Second unsupported relationship.'])
        self.reject_mapping('Final rejection.')
        with patch('x_curator.wiki_mapping.runner') as runner:
            with self.assertRaisesRegex(ValueError, 'budget exhausted'):
                map_sources(self.db, self.inputs)
        runner.assert_not_called()
        self.assertEqual(self.db.execute('SELECT attempts FROM wiki_sources').fetchone()[0], 3)
