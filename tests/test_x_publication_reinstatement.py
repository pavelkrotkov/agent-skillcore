import json
from unittest.mock import patch

from x_quick_fixtures import QuickCase
from x_curator import publication_audit, quick_process
from x_curator.publication_recovery import complete
from x_curator.receipts import digest


class PublicationReinstatementTests(QuickCase):
    def setUp(self):
        super().setUp()
        with patch('x_curator.quick_web.fetch', self.fetch), patch('x_curator.quick_search.fetch', self.fetch), patch('x_curator.quick_process.runner', return_value=self.checker):
            self.identity = quick_process.research(self.db, self.root, self.client, self.token)
        self.withdraw()

    def withdraw(self):
        with patch('x_curator.publication_audit.verify_publication', side_effect=ValueError('synthetic verifier defect')):
            self.assertEqual(publication_audit.audit(self.db, self.root), [self.identity])

    def history(self):
        tables = ('attempts', 'executions', 'quick_checks', 'retrievals', 'captures', 'publication_audit_failures')
        return {table: [tuple(row) for row in self.db.execute('SELECT * FROM '+table)] for table in tables}

    def test_reinstatement_preserves_completed_check_and_original_proof_without_execution(self):
        before = self.history()
        budget = tuple(self.db.execute('SELECT attempts,max_attempts FROM jobs').fetchone())
        with patch('x_curator.publication_recovery.published', side_effect=AssertionError('completed check must remain unchanged')):
            recovered = complete(self.db, self.root, self.identity, 'Current exact proof passes after verifier repair')
            repeated = complete(self.db, self.root, self.identity, 'Repeated exact request')
        self.assertFalse(recovered['already_completed'])
        self.assertTrue(repeated['already_completed'])
        self.assertEqual(self.history(), before)
        self.assertEqual(tuple(self.db.execute('SELECT attempts,max_attempts FROM jobs').fetchone()), budget)
        self.assertEqual(publication_audit.audit(self.db, self.root), [])
        row = self.db.execute('SELECT * FROM publication_reinstatements').fetchone()
        receipt = json.loads(row['receipt'])
        self.assertEqual((row['id'], receipt['prior_publication_state']), (digest(receipt), 'invalid'))

    def test_second_withdrawal_appends_event_without_rewriting_first_recovery(self):
        complete(self.db, self.root, self.identity, 'First verified reinstatement')
        original = tuple(self.db.execute('SELECT * FROM publication_recoveries').fetchone())
        first = tuple(self.db.execute('SELECT * FROM publication_reinstatements').fetchone())
        self.withdraw()
        before = self.history()
        complete(self.db, self.root, self.identity, 'Second independently verified reinstatement')
        self.assertEqual(self.history(), before)
        self.assertEqual(tuple(self.db.execute('SELECT * FROM publication_recoveries').fetchone()), original)
        events = [tuple(row) for row in self.db.execute('SELECT * FROM publication_reinstatements ORDER BY rowid')]
        self.assertEqual((len(events), events[0]), (2, first))
