import json

from x_review_fixtures import ReviewCase
from x_curator import batch_report, review_outbox


class ReviewTests(ReviewCase):
    def test_mixed_decisions_are_durable_scoped_and_do_not_start_work(self):
        value = self.prepare(3)
        self.observe()
        a, b, c = self.references
        self.reply(f'research {a}; defer {b}; exclude {c}')
        self.reply(f'research {a}; defer {b}; exclude {c}')
        permissions = list(self.db.execute('SELECT * FROM research_permissions'))
        self.assertEqual(len(permissions), 1)
        permission = dict(permissions[0])
        proposal = json.loads(value['payload'])['review'][0]
        for key in ('source', 'revision', 'question', 'scope', 'seconds'):
            self.assertEqual(permission[key], proposal[key])
        self.assertIsNone(permission['consumed'])
        self.assertEqual(self.run_batch()['attempted'], 0)
        self.assertEqual(self.db.execute("SELECT state FROM jobs WHERE id=?", (proposal['source'],)).fetchone()[0], 'awaiting_review')
        self.assertEqual(self.db.execute('SELECT count(*) FROM review_replies').fetchone()[0], 1)
        self.assertEqual(review_outbox.prepare(self.db, value['batch'], value['chat'])['id'], value['id'])
        self.assertEqual(review_outbox.status(self.db)['deliveries'][0]['decisions'], 3)

    def test_no_empty_or_partial_digest_and_no_chat_rebinding(self):
        self.add_items(2)
        self.checker = self.pending
        self.run_batch(limit=1)
        batch = batch_report.report(self.db)['batches'][0]
        with self.assertRaises(ValueError):
            review_outbox.prepare(self.db, batch['id'], 'synthetic-chat')
        self.run_batch()
        value = review_outbox.prepare(self.db, batch['id'], 'synthetic-chat')
        with self.assertRaises(ValueError):
            review_outbox.prepare(self.db, batch['id'], 'other-chat')
        self.assertEqual(len(json.loads(value['payload'])['review']), 2)

    def test_supported_batch_needs_no_approval_request(self):
        self.run_batch()
        batch = batch_report.report(self.db)['batches'][0]
        self.assertIsNone(review_outbox.prepare(self.db, batch['id'], 'synthetic-chat'))
