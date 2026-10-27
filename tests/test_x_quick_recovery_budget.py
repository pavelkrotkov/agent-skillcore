import json
import time

from x_quick_recovery_fixtures import RecoveryCase
from x_curator import quick_recovery, quick_store
from x_curator.leases import claim, fail
from x_fixtures import Client


class QuickRecoveryBudgetTests(RecoveryCase):
    def test_replacement_keeps_history_bounded_allowance_and_rejects_old_approval(self):
        original = self.affected()
        message = self.value['message']
        plan = quick_recovery.run(self.db)
        self.assertEqual(len(plan['items']), 1)
        quick_recovery.run(self.db, plan['digest'])
        with self.assertRaises(ValueError):
            quick_recovery.run(self.db, plan['digest'])
        self.assertEqual(quick_recovery.run(self.db)['items'], [])
        self.assertEqual(dict(self.db.execute('SELECT * FROM quick_checks WHERE id=?', (original['id'],)).fetchone()), original)
        self.assertEqual(self.db.execute('SELECT message FROM review_deliveries WHERE id=?', (self.value['id'],)).fetchone()[0], message)
        with self.assertRaisesRegex(ValueError, 'superseded'):
            self.reply('research ' + self.references[0])
        self.token = claim(self.db, Client.account, 180)['token']
        check = quick_store.start(self.db, self.token, time.time())
        self.assertNotEqual(check['id'], original['id'])
        for _ in range(3):
            quick_store.reserve_search(self.db, self.token)
        with self.assertRaises(ValueError):
            quick_store.reserve_search(self.db, self.token)
        with self.db:
            self.db.execute('UPDATE jobs SET max_attempts=attempts+1')
        fail(self.db, self.token, 'synthetic interruption', 0)
        self.token = claim(self.db, Client.account, 180)['token']
        resumed = quick_store.start(self.db, self.token, time.time())
        self.assertEqual((resumed['deadline'], resumed['searches']), (check['deadline'], 3))
        self.assertEqual(resumed['deadline'] - resumed['started'], 120)


    def test_intentional_search_endpoint_read_guard_is_not_a_repaired_bug(self):
        self.affected()
        error = json.dumps({'isError': True, 'content': [{'type': 'text', 'text': 'search engine URLs cannot be read as sources'}]})
        with self.db:
            self.db.execute('UPDATE quick_tools SET output=?', (error,))
        self.assertEqual(quick_recovery.run(self.db)['items'], [])
        with self.db:
            self.db.execute("UPDATE quick_tools SET name='search'")
        self.assertEqual(len(quick_recovery.run(self.db)['items']), 1)
