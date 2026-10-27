from x_review_fixtures import ReviewCase, readback
from x_curator import review_decisions, review_receipts


class ReviewGuardTests(ReviewCase):
    def test_delivery_requires_exact_native_destination_and_complete_body(self):
        value = self.prepare()
        for chat, text, kind in [('other', value['message'], 'agentMessage'),
                                 (value['chat'], value['message'][:100], 'agentMessage'),
                                 (value['chat'], value['message'], 'userMessage')]:
            with self.assertRaises(ValueError):
                review_receipts.observe(self.db, value['id'], readback(chat, 'm', text, kind), 'm')
        self.assertIsNone(self.db.execute('SELECT observed FROM review_deliveries').fetchone()[0])
        review_receipts.failed(self.db, value['id'], 'Native delivery unavailable')
        self.observe()
        self.assertIsNone(self.db.execute('SELECT failure FROM review_deliveries').fetchone()[0])

    def test_unobserved_and_nonhuman_replies_cannot_authorize(self):
        value = self.prepare()
        clause = 'research ' + self.references[0]
        with self.assertRaises(ValueError):
            self.reply(clause)
        self.observe()
        receipt = readback(value['chat'], 'm', 'review ' + value['id'] + '; ' + clause, 'userMessage')
        with self.assertRaises(ValueError):
            review_decisions.apply(self.db, value['id'], receipt, 'm')
        receipt['turns'][0]['items'][0]['type'] = 'agentMessage'
        with self.assertRaises(ValueError):
            review_decisions.apply(self.db, value['id'], receipt, 'm', human_origin_confirmed=True)
        self.assertEqual(self.db.execute('SELECT count(*) FROM research_permissions').fetchone()[0], 0)

    def test_ambiguous_or_conflicting_replies_fail_atomically(self):
        self.prepare(2)
        self.observe()
        a, b = self.references
        for clause in ('yes', 'research 1', f'research {a}; exclude {a}', f'research {a}; perhaps {b}'):
            with self.assertRaises(ValueError):
                self.reply(clause)
        self.assertEqual(self.db.execute('SELECT count(*) FROM review_decisions').fetchone()[0], 0)
        self.reply(f'exclude {a}')
        with self.assertRaises(ValueError):
            self.reply(f'research {b}; research {a}', identity='second-human')
        self.assertEqual(self.db.execute('SELECT count(*) FROM research_permissions').fetchone()[0], 0)
