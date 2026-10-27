import time

from x_quick_recovery_fixtures import RecoveryCase
from x_curator import quick_recovery, quick_store, review_generation
from x_curator.leases import claim
from x_curator.quick_replacements import latest
from x_fixtures import Client


class ReplacementChainTests(RecoveryCase):
    def test_approved_second_replacement_is_fresh_and_preserves_prior_receipts(self):
        original = self.affected()
        with self.db:
            self.db.execute('UPDATE jobs SET max_attempts=4')
        plan = quick_recovery.run(self.db)
        quick_recovery.run(self.db, plan['digest'])
        self.token = claim(self.db, Client.account, 180)['token']
        first = quick_store.start(self.db, self.token, time.time())
        quick_store.finish(self.db, self.token, 'inconclusive', 'synthetic repaired failure')
        retained = [dict(row) for row in self.db.execute('SELECT * FROM quick_checks ORDER BY started')]
        grants = self.db.execute('SELECT count(*) FROM recovery_grants').fetchone()[0]
        with self.db:
            self.db.execute('INSERT INTO quick_recoveries VALUES(?,?,?,?,?,?,NULL)',
                            (first['id'], 'second', Client.account, original['source'], time.time(), 'explicit new approval'))
            self.db.execute("UPDATE jobs SET state='retry'")
        self.token = claim(self.db, Client.account, 180)['token']
        second = quick_store.start(self.db, self.token, time.time())
        self.assertEqual(second['id'], 'second')
        self.assertEqual(second['deadline'] - second['started'], 120)
        self.assertGreater(second['started'], first['started'])
        self.assertEqual([dict(row) for row in self.db.execute('SELECT * FROM quick_checks WHERE id!=?', ('second',))], retained)
        self.assertEqual(self.db.execute('SELECT count(*) FROM recovery_grants').fetchone()[0], grants)
        item = dict(source=original['source'], revision=original['revision'], check=first['id'])
        with self.assertRaisesRegex(ValueError, 'superseded'):
            review_generation.require_current(self.db, Client.account, item)
        review_generation.require_current(self.db, Client.account, dict(item, check='second'))

    def test_foreign_replacements_and_cycles_cannot_spend_a_new_check(self):
        original = self.affected()
        with self.assertRaisesRegex(ValueError, 'job is missing'):
            latest(self.db, Client.account, 'missing', original['id'])
        plan = quick_recovery.run(self.db)
        quick_recovery.run(self.db, plan['digest'])
        with self.db:
            self.db.execute("UPDATE quick_recoveries SET account='foreign'")
        with self.assertRaisesRegex(ValueError, 'another source'):
            latest(self.db, Client.account, original['source'], original['id'])
        with self.db:
            self.db.execute('UPDATE quick_recoveries SET account=?,replacement=?', (Client.account, original['id']))
        with self.assertRaisesRegex(ValueError, 'attempt bound'):
            latest(self.db, Client.account, original['source'], original['id'])
