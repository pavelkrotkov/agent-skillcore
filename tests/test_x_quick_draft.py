import copy
import json
import time
from unittest.mock import patch

from x_quick_fixtures import QuickCase, native
from x_curator import quick_mcp, quick_store
from x_curator.publication_audit import audit
import test_x_quick_flow


class QuickDraftTests(QuickCase):
    run_check = test_x_quick_flow.QuickFlowTests.run_check

    def checker(self, request):
        found = quick_mcp.call(self.db, self.token, 'search', {'query': 'synthetic release'})
        source = json.loads(found['content'][0]['text'])[0]['source']
        read = quick_mcp.call(self.db, self.token, 'read', {'source': source})
        decision = self.packet_for(json.loads(read['content'][0]['text'])['capture'])
        invalid = copy.deepcopy(decision)
        invalid['checks'][0]['sources'][0]['quote'] = 'Invented evidence'
        before = dict(quick_store.active(self.db, self.token))
        rejected = quick_mcp.call(self.db, self.token, 'validate', {'decision': invalid})
        self.assertTrue(rejected['isError'])
        self.assertIn('excerpt is absent', rejected['content'][0]['text'])
        invalid['checks'][0]['sources'][0]['capture'] = next(iter(request['bundle']['captures']))
        wrong_kind = quick_mcp.call(self.db, self.token, 'validate', {'decision': invalid})
        self.assertTrue(wrong_kind['isError'])
        self.assertIn('observed source body', wrong_kind['content'][0]['text'])
        accepted = quick_mcp.call(self.db, self.token, 'validate', {'decision': decision})
        self.assertFalse(accepted['isError'])
        self.assertEqual(dict(quick_store.active(self.db, self.token)), before)
        self.assertEqual(self.db.execute('SELECT count(*) FROM publications').fetchone()[0], 0)
        return native(request, self.modify(decision), [found, read, rejected, wrong_kind, accepted])

    def test_invalid_draft_can_be_corrected_in_same_execution_without_new_allowance(self):
        self.assertIsNotNone(self.run_check())
        self.assertEqual(audit(self.db, self.root), [])
        self.assertEqual(self.db.execute('SELECT count(*) FROM executions').fetchone()[0], 1)
        self.assertEqual(len(self.calls), 2)

    def test_passing_draft_does_not_authorize_invalid_final_answer(self):
        def corrupt(value):
            value['checks'][0]['sources'][0]['quote'] = 'Invented final quotation'
            return value
        self.modify = corrupt
        self.assertIsNone(self.run_check())
        self.assertEqual(self.db.execute('SELECT count(*) FROM publications').fetchone()[0], 0)

    def test_validation_after_deadline_does_not_run_or_extend_budget(self):
        before = quick_store.start(self.db, self.token, time.time() - 121)
        with patch('x_curator.quick_packet.validate', side_effect=AssertionError('expired validation')):
            result = quick_mcp.call(self.db, self.token, 'validate', {'decision': {}})
        self.assertTrue(result['isError'])
        after = dict(self.db.execute('SELECT * FROM quick_checks').fetchone())
        self.assertEqual(after['deadline'], before['deadline'])
        self.assertEqual(after['searches'], 0)
