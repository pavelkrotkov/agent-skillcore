from x_daily_fixtures import DailyCase
from x_curator import batch_report, daily_store, review_outbox
from x_curator.wiki_current import current
from x_fixtures import Client


class DailyTests(DailyCase):
    def test_daily_and_backlog_alternate_and_pending_items_make_one_daily_digest(self):
        capture = self.intake([2, 3], self.baseline + 10)
        self.checker = self.pending
        result = self.daily_work()
        batches = {b['id']: b for b in batch_report.report(self.db)['batches']}
        self.assertEqual([batches[r['batch']]['kind'] for r in result['results']], ['daily', 'backlog', 'daily'])
        daily = next(b for b in batches.values() if b['kind'] == 'daily')
        self.assertEqual(daily['counts'], {'pending_decision': 2})
        self.assertEqual(len(review_outbox.status(self.db)['deliveries']), 2)
        self.assertEqual(self.daily_work()['attempted'], 0)
        self.assertEqual(len(review_outbox.status(self.db)['deliveries']), 2)
        self.assertFalse(capture['historical_complete'])

    def test_arrival_after_cutoff_waits_and_supported_items_publish_without_waiting_for_review(self):
        self.intake([2], self.baseline + 10)
        self.intake([3], self.cutoff + 1)
        result = self.daily_work()
        self.assertEqual(result['completed'], 2)
        self.assertEqual(len(current(self.db, self.root)['sources']), 2)
        self.assertEqual(self.db.execute("SELECT count(*) FROM curation_members WHERE source='3'").fetchone()[0], 0)
        self.assertEqual(review_outbox.status(self.db)['deliveries'], [])
        self.cutoff += 86400
        result = self.daily_work()
        self.assertEqual(result['completed'], 1)
        self.assertEqual(len(current(self.db, self.root)['sources']), 3)
        self.assertEqual(self.db.execute('SELECT count(*) FROM publications').fetchone()[0], 3)

    def test_repeated_setup_preserves_baseline_and_rejects_implicit_reclassification(self):
        initial = daily_store.settings(self.db, Client.account)
        self.assertEqual(daily_store.configure(self.db, Client.account, 'synthetic-chat', 'America/New_York')['baseline'], initial['baseline'])
        with self.assertRaises(ValueError):
            daily_store.configure(self.db, Client.account, 'synthetic-chat', 'UTC')
        with self.assertRaises(ValueError):
            daily_store.configure(self.db, Client.account, 'other-chat', 'America/New_York')
        self.assertEqual(daily_store.settings(self.db, Client.account), initial)
