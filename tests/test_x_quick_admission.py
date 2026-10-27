import json
from unittest.mock import patch

import test_x_quick_flow
from x_quick_fixtures import QuickCase
from x_curator.receipts import encoded


class QuickAdmissionTests(QuickCase):
    run_check = test_x_quick_flow.QuickFlowTests.run_check

    def test_unrelated_fact_cannot_borrow_supported_check(self):
        def unrelated(value):
            value['packet']['claims'][0]['text'] = 'The moon consists entirely of cheese.'
            return value
        self.modify = unrelated
        self.assertIsNone(self.run_check())
        self.assertEqual(self.db.execute('SELECT state FROM jobs').fetchone()[0], 'awaiting_review')

    def test_repeated_origin_cannot_establish_independent_corroboration(self):
        def duplicate(value):
            source = value['checks'][0]['sources'][0]
            source['primary'] = False
            value['checks'][0]['sources'].append(dict(source, origin='Different label'))
            return value
        self.modify = duplicate
        self.assertIsNone(self.run_check())
        self.assertEqual(self.db.execute('SELECT outcome FROM quick_checks').fetchone()[0], 'inconclusive')

    def test_publication_failure_downgrades_check_and_job_consistently(self):
        with patch('x_curator.quick_process.publish', side_effect=OSError('synthetic disk failure')):
            self.assertIsNone(self.run_check())
        self.assertEqual(self.db.execute('SELECT outcome FROM quick_checks').fetchone()[0], 'inconclusive')
        self.assertEqual(self.db.execute('SELECT state FROM jobs').fetchone()[0], 'awaiting_review')

    def test_tool_evidence_after_answer_cannot_support_exclusion(self):
        original = self.checker
        def late(request):
            proof = json.loads(original(request))
            rows = [json.loads(line) for line in proof['rollout'].splitlines()]
            rows.insert(2, rows.pop())
            proof['rollout'] = '\n'.join(json.dumps(row) for row in rows)
            return encoded(proof)
        def disprove(value):
            value['checks'][0]['status'] = 'disproven'
            value.update(outcome='disproven')
            value.pop('packet')
            return value
        self.modify = disprove
        self.checker = late
        self.assertIsNone(self.run_check())
        self.assertEqual(self.db.execute('SELECT state FROM jobs').fetchone()[0], 'awaiting_review')

    def test_useful_attributed_opinion_keeps_checked_factual_details(self):
        def opinion(value):
            claim = value['packet']['claims'][0]
            claim.update(kind='recommendation', text='The author recommends the tool released in 2025.')
            return value
        self.modify = opinion
        self.assertIsNotNone(self.run_check())

    def test_crash_before_publication_does_not_record_supported_outcome(self):
        with patch('x_curator.quick_process.publish', side_effect=SystemExit('synthetic process crash')):
            with self.assertRaises(SystemExit):
                self.run_check()
        self.assertIsNone(self.db.execute('SELECT outcome FROM quick_checks').fetchone()[0])
        self.assertEqual(self.db.execute('SELECT count(*) FROM publications').fetchone()[0], 0)

    def test_fact_cannot_replace_checked_support_with_original_tweet(self):
        def replace_citation(value):
            value['packet']['claims'][0]['citations'] = self.packet['claims'][0]['citations']
            return value
        self.modify = replace_citation
        self.assertIsNone(self.run_check())

    def test_mixed_item_retains_useful_supported_part_only(self):
        def mixed(value):
            value['checks'].append(dict(id='f2', text='Unsupported peripheral assertion.', status='inconclusive', sources=[]))
            return value
        self.modify = mixed
        self.assertIsNotNone(self.run_check())
        self.assertEqual(self.db.execute('SELECT outcome FROM quick_checks').fetchone()[0], 'supported')

    def test_native_code_mode_tool_outputs_are_observed_before_answer(self):
        original = self.checker
        def code_mode(request):
            proof = json.loads(original(request))
            rows = [json.loads(line) for line in proof['rollout'].splitlines()]
            for row in rows:
                payload = row['payload']
                if payload.get('type') == 'function_call_output':
                    payload.update(type='custom_tool_call_output', output=[{'type': 'input_text', 'text': payload['output']}])
            proof['rollout'] = '\n'.join(json.dumps(row) for row in rows)
            return encoded(proof)
        self.checker = code_mode
        self.assertIsNotNone(self.run_check())
