import json

from x_review_fixtures import ReviewCase, readback
from x_curator import review_native, review_receipts


class ReviewNewlineTests(ReviewCase):
    def test_transport_newline_preserves_complete_receipt_binding(self):
        value = self.prepare()
        for text in (value['message'] + '\n\n', value['message'] + '\nextra',
                     value['message'].replace('Maximum:', 'Changed:')):
            with self.assertRaises(ValueError):
                review_receipts.observe(self.db, value['id'], readback(value['chat'], 'm', text), 'm')
        receipt = readback(value['chat'], 'm', value['message'] + '\n')
        review_receipts.observe(self.db, value['id'], receipt, 'm')
        stored = dict(self.db.execute('SELECT * FROM review_deliveries').fetchone())
        self.assertEqual(json.loads(stored['observed'])['receipt'], receipt)
        review_native.require_observed(stored)
        self.assertEqual(self.db.execute('SELECT count(*) FROM research_permissions').fetchone()[0], 0)
