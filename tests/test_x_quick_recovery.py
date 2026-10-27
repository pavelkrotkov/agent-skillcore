import json

from x_quick_recovery_fixtures import RecoveryCase
from x_curator import batch_report, quick_recovery, review_reconcile
from x_fixtures import Client


class QuickRecoveryTests(RecoveryCase):
    def test_completed_replacement_gets_one_fresh_digest_without_old_permissions(self):
        self.affected()
        old_delivery = self.value['id']
        plan = quick_recovery.run(self.db)
        quick_recovery.run(self.db, plan['digest'])
        self.checker = self.pending
        self.run_batch(1)
        review_reconcile.flush(self.db, Client.account)
        second = review_reconcile.flush(self.db, Client.account)
        self.assertEqual(second, [])
        rows = self.db.execute('SELECT * FROM review_deliveries WHERE id!=?', (old_delivery,)).fetchall()
        self.assertEqual(len(rows), 1)
        with self.assertRaisesRegex(ValueError, 'superseded'):
            self.reply('research ' + self.references[0])
        self.value = dict(rows[0])
        self.references = [json.loads(self.value['payload'])['review'][0]['reference']]
        self.observe()
        self.reply('research ' + self.references[0])
        self.assertEqual(self.db.execute('SELECT count(*) FROM research_permissions').fetchone()[0], 1)
        self.assertEqual(len(batch_report.report(self.db)['batches']), 2)

    def test_human_defer_and_unaffected_checks_do_not_get_recovery(self):
        self.affected()
        self.reply('defer ' + self.references[0])
        self.assertEqual(quick_recovery.run(self.db)['items'], [])

    def test_supported_replacement_does_not_create_an_empty_review_batch(self):
        self.affected()
        plan = quick_recovery.run(self.db)
        quick_recovery.run(self.db, plan['digest'])
        self.checker = super().checker
        self.run_batch(1)
        review_reconcile.flush(self.db, Client.account)
        batches = batch_report.report(self.db)['batches']
        self.assertEqual(len(batches), 1)
        self.assertEqual(batches[0]['counts'], {'supported': 1})

    def test_new_original_digest_already_covering_replacement_is_not_duplicated(self):
        self.affected()
        with self.db:
            self.db.execute('DELETE FROM review_deliveries')
        plan = quick_recovery.run(self.db)
        quick_recovery.run(self.db, plan['digest'])
        self.checker = self.pending
        self.run_batch(1)
        review_reconcile.flush(self.db, Client.account)
        self.assertEqual(self.db.execute('SELECT count(*) FROM review_deliveries').fetchone()[0], 1)
        self.assertEqual(len(batch_report.report(self.db)['batches']), 1)
