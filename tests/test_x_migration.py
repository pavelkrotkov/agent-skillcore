import json

from x_batch_fixtures import BatchCase
from x_curator import policy_migration
from x_curator.leases import claim
from x_fixtures import Client
from x_curator.recovery import request_limit
from x_curator.retrieval_store import initialize


class MigrationTests(BatchCase):
    def preview(self):
        return policy_migration.preview(self.root)

    def test_preview_is_read_only_and_stale_plan_cannot_apply(self):
        before = list(self.db.iterdump())
        plan = self.preview()
        self.assertEqual(list(self.db.iterdump()), before)
        self.assertEqual(plan['counts'], {'quick_check': 1})
        with self.db:
            self.db.execute("UPDATE jobs SET action='new operator diagnosis'")
        with self.assertRaises(ValueError):
            policy_migration.apply(self.root, plan['digest'])
        self.assertEqual(self.db.execute('SELECT count(*) FROM policy_transitions').fetchone()[0], 0)
        self.assertEqual(self.db.execute('SELECT state FROM jobs').fetchone()[0], 'retry')

    def test_exhausted_history_gets_one_explicit_grant_and_replay_never_refills(self):
        initialize(self.db)
        with self.db:
            self.db.execute("UPDATE jobs SET state='needs_action',attempts=5,max_attempts=5,action='old rejection'")
            self.db.executemany('INSERT INTO retrievals(id,token,account,source,url,started) VALUES (?,?,?,?,?,?)',
                [(str(i), self.token, Client.account, '1', 'https://example.test', i) for i in range(40)])
        before = [tuple(r) for r in self.db.execute('SELECT * FROM attempts')]
        plan = self.preview()
        self.assertEqual(plan['items'][0]['grant']['request_extra'], 20)
        self.assertEqual(plan['items'][0]['grant']['remaining_requests'], 20)
        policy_migration.apply(self.root, plan['digest'])
        job = self.db.execute('SELECT * FROM jobs').fetchone()
        self.assertEqual((job['state'], job['attempts'], job['max_attempts']), ('pending', 5, 6))
        self.assertEqual([tuple(r) for r in self.db.execute('SELECT * FROM attempts')], before)
        prior = json.loads(self.db.execute('SELECT prior FROM policy_transitions').fetchone()[0])
        self.assertEqual(prior['job']['action'], 'old rejection')
        self.assertEqual(request_limit(self.db, job['account'], '1'), 60)
        again = self.preview()
        policy_migration.apply(self.root, again['digest'])
        self.assertEqual(self.db.execute('SELECT count(*) FROM recovery_grants').fetchone()[0], 1)
        self.assertEqual(self.db.execute('SELECT count(*) FROM retrievals').fetchone()[0], 40)

    def test_missing_captured_job_is_created_only_on_apply(self):
        self.add_items(2)
        plan = self.preview()
        self.assertEqual(plan['captured'], 2)
        self.assertEqual(self.db.execute('SELECT count(*) FROM jobs').fetchone()[0], 1)
        policy_migration.apply(self.root, plan['digest'])
        self.assertEqual(self.db.execute('SELECT count(*) FROM jobs').fetchone()[0], 2)

    def test_live_lease_and_orphan_block_entire_apply(self):
        claim(self.db, Client.account)
        plan = self.preview()
        self.assertTrue(plan['blockers'])
        with self.assertRaises(ValueError):
            policy_migration.apply(self.root, plan['digest'])
        with self.db:
            self.db.execute("INSERT INTO jobs(account,id,created) VALUES ('synthetic-orphan','orphan',0)")
        self.assertEqual(len(self.preview()['blockers']), 2)

    def test_verified_publication_and_new_policy_dispositions_are_preserved(self):
        self.run_batch()
        before = list(self.db.iterdump())
        plan = self.preview()
        self.assertEqual(plan['counts'], {'valid_publication': 1})
        self.assertEqual(list(self.db.iterdump()), before)
        policy_migration.apply(self.root, plan['digest'])
        self.assertEqual(self.db.execute('SELECT count(*) FROM recovery_grants').fetchone()[0], 0)
        page = self.db.execute('SELECT path FROM publications').fetchone()[0]
        (self.root / page).write_text('damaged')
        self.assertEqual(self.preview()['counts'], {'blocked': 1})

    def test_pending_decision_is_never_automatically_researched(self):
        self.checker = self.pending
        self.run_batch()
        plan = self.preview()
        self.assertEqual(plan['counts'], {'preserve_new_policy': 1})
        policy_migration.apply(self.root, plan['digest'])
        self.assertEqual(self.db.execute('SELECT state FROM jobs').fetchone()[0], 'awaiting_review')
        self.assertEqual(self.db.execute('SELECT count(*) FROM recovery_grants').fetchone()[0], 0)
