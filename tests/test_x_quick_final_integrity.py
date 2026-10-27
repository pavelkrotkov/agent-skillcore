import copy
import json
from test_x_quick_final import FinalCase
from x_curator import quick_mcp
from x_curator.publication_audit import audit
from x_curator.receipts import digest, encoded


class QuickFinalIntegrityTests(FinalCase):
    def test_wrong_reference_cannot_publish(self):
            self.assertIsNone(self.run_final(lambda value: dict(value, decision_sha='0' * 64)))
            self.assertEqual(self.db.execute('SELECT count(*) FROM publications').fetchone()[0], 0)

    def test_failed_draft_reference_cannot_publish(self):
            def rejected(value):
                invalid = copy.deepcopy(self.validated)
                invalid['checks'][0]['sources'][0]['quote'] = 'Invented quote.'
                self.rejected = quick_mcp.call(self.db, self.token, 'validate', {'decision': invalid})
                self.assertTrue(self.rejected['isError'])
                return dict(value, decision_sha=digest(invalid))
            self.assertIsNone(self.run_final(rejected))
            self.assertEqual(self.db.execute('SELECT count(*) FROM publications').fetchone()[0], 0)

    def test_foreign_validator_receipt_cannot_publish(self):
            def foreign(value):
                with self.db:
                    self.db.execute("UPDATE quick_tools SET token='foreign' WHERE name='validate'")
                return value
            self.assertIsNone(self.run_final(foreign))
            self.assertEqual(self.db.execute('SELECT count(*) FROM publications').fetchone()[0], 0)

    def test_tampered_validated_draft_invalidates_publication(self):
            self.assertIsNotNone(self.run_final())
            row = self.db.execute("SELECT id,arguments FROM quick_tools WHERE name='validate'").fetchone()
            value = json.loads(row['arguments'])
            value['decision']['reason'] = 'Tampered reason.'
            with self.db:
                self.db.execute('UPDATE quick_tools SET arguments=? WHERE id=?', (encoded(value).decode(), row['id']))
            self.assertTrue(audit(self.db, self.root))
