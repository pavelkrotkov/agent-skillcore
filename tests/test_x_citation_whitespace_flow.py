import json

from test_x_quick_final import FinalCase
from x_curator.publication_audit import audit
from x_curator.receipts import digest


class CitationWhitespaceFlowTests(FinalCase):
    def fetch(self, url):
        status, mime, body, error = super().fetch(url)
        return status, mime, body.replace(b'was released', b'was\nreleased'), error

    def test_normalized_quote_preserves_native_receipts_and_publication_audit(self):
        self.assertIsNotNone(self.run_final())
        tool = self.db.execute("SELECT arguments FROM quick_tools WHERE name='validate'").fetchone()
        decision = json.loads(tool['arguments'])['decision']
        self.assertEqual(digest(decision), self.response['decision_sha'])
        self.assertEqual(decision['checks'][0]['sources'][0]['quote'], 'The tool was released in 2025.')
        self.assertEqual(audit(self.db, self.root), [])
        with self.db:
            self.db.execute("UPDATE quick_tools SET output=replace(output,'2025','2024') WHERE name='read'")
        self.assertTrue(audit(self.db, self.root))

    def test_whitespace_equivalent_contradiction_can_exclude_without_publication(self):
        def disprove(value):
            value['checks'][0]['status'] = 'disproven'
            value.update(outcome='disproven', reason='Original evidence disproves the central claim.')
            value.pop('packet')
            return value
        self.modify = disprove
        self.assertIsNone(self.run_final())
        self.assertEqual(self.db.execute('SELECT state FROM jobs').fetchone()[0], 'excluded')
        self.assertEqual(self.db.execute('SELECT count(*) FROM publications').fetchone()[0], 0)
