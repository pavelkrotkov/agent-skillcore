import json

from x_deep_fixtures import DeepCase
from x_curator import deep_process, deep_review
from x_curator.publication_audit import audit


class DeepTests(DeepCase):
    def test_matching_approval_publishes_without_changing_the_original_quick_record(self):
        self.authorize()
        original = dict(self.db.execute('SELECT * FROM quick_checks').fetchone())
        self.checker = super().checker
        result = self.deep()
        self.assertEqual(result['state'], 'published')
        self.assertEqual(audit(self.db, self.root), [])
        self.assertEqual(dict(self.db.execute('SELECT * FROM quick_checks').fetchone()), original)
        self.assertEqual(self.db.execute('SELECT outcome FROM deep_runs').fetchone()[0], 'supported')
        with self.assertRaises(ValueError):
            self.deep()
        self.assertEqual(self.db.execute('SELECT count(*) FROM publications').fetchone()[0], 1)

    def test_unresolved_run_returns_once_to_later_batch_and_extension_is_separately_approved(self):
        self.authorize()
        self.assertEqual(self.deep()['state'], 'awaiting_review')
        account = self.db.execute('SELECT account FROM research_permissions').fetchone()[0]
        value = deep_review.prepare(self.db, account, 'synthetic-chat')
        self.assertIsNone(deep_review.prepare(self.db, account, 'synthetic-chat'))
        original = value['message']
        extended = deep_review.prepare(self.db, account, 'synthetic-chat', self.approval, 900)
        self.assertEqual(deep_review.prepare(self.db, account, 'synthetic-chat', self.approval, 900)['id'], extended['id'])
        self.assertNotEqual(value['id'], extended['id'])
        self.assertEqual(self.db.execute('SELECT message FROM review_deliveries WHERE id=?', (value['id'],)).fetchone()[0], original)
        self.value = extended
        self.references = [i['reference'] for i in json.loads(extended['payload'])['review']]
        self.observe()
        self.reply('research ' + self.references[0], identity='explicit-extension')
        self.approval = self.db.execute('SELECT id FROM research_permissions WHERE consumed IS NULL').fetchone()[0]
        self.checker = super().checker
        self.assertEqual(self.deep()['state'], 'published')
        run = self.db.execute('SELECT * FROM deep_runs WHERE id=?', (self.approval,)).fetchone()
        self.assertEqual(run['deadline'] - run['started'], 900)

    def test_no_permission_or_tampered_permission_cannot_start(self):
        self.authorize()
        with self.assertRaises(ValueError):
            deep_process.work(self.db, self.root, 'unknown-approval')
        with self.db:
            self.db.execute('UPDATE research_permissions SET seconds=3600')
        with self.assertRaises(ValueError):
            self.deep()
        self.assertEqual(self.db.execute('SELECT count(*) FROM deep_runs').fetchone()[0], 0)
