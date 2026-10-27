import json
from unittest.mock import patch
from x_native_search_fixtures import NativeCase
from x_quick_fixtures import native
from x_curator.publication_audit import audit
from x_curator.receipts import digest, encoded

FORMAT = 'curator-validated-decision-v1'

class FinalCase(NativeCase):
    def terminal(self, request, decision, responses, searches):
            self.validated = decision
            self.response = json.loads(responses[-1]['content'][0]['text'])
            final = {'format': FORMAT, 'decision_sha': digest(decision)}
            return native(request, self.change(final), responses, searches)

    def run_final(self, change=lambda value: value):
            self.change = change
            with patch('x_native_search_fixtures.native', side_effect=self.terminal):
                return self.run_check()


class QuickFinalTests(FinalCase):
    def test_validated_reference_publishes_and_replays_without_repeated_decision(self):
            self.assertIsNotNone(self.run_final())
            output = json.loads(self.db.execute('SELECT output FROM executions').fetchone()[0])
            self.assertEqual(output, {'format': FORMAT, 'decision_sha': digest(self.validated)})
            self.assertEqual(self.response['decision_sha'], output['decision_sha'])
            self.assertGreaterEqual(self.response['remaining_seconds'], 0)
            self.assertLessEqual(self.response['remaining_seconds'], 120)
            self.assertEqual(audit(self.db, self.root), [])
            self.assertEqual(self.db.execute('SELECT count(*) FROM attempts').fetchone()[0], 1)

    def test_validation_without_completed_model_turn_cannot_publish(self):
            def incomplete(request, decision, responses, searches):
                log = json.loads(self.terminal(request, decision, responses, searches))
                log['events'] = '\n'.join(log['events'].strip().split('\n')[:-1]) + '\n'
                return encoded(log)
            self.change = lambda value: value
            with patch('x_native_search_fixtures.native', side_effect=incomplete):
                self.assertIsNone(self.run_check())
            self.assertEqual(self.db.execute('SELECT count(*) FROM publications').fetchone()[0], 0)
