from x_quick_recovery_fixtures import RecoveryCase
from x_curator import native_search, policy_migration, quick_recovery
from x_curator.receipts import digest


class NativePolicyTests(RecoveryCase):
    def test_recovery_preview_discloses_target_and_rejects_old_policy_digest(self):
        self.affected()
        plan = quick_recovery.run(self.db)
        self.assertEqual((plan['seconds'], plan['search_target'], plan['search_limit']), (120, 3, None))
        self.assertEqual(plan['search_mode'], native_search.MODE)
        before = list(self.db.iterdump())
        with self.assertRaisesRegex(ValueError, 'preview changed'):
            quick_recovery.run(self.db, digest(['retrieval-repair/v1', plan['items']]))
        self.assertEqual(list(self.db.iterdump()), before)
        self.assertEqual(plan['items'][0]['replacement'], digest(['retrieval-repair/v1', plan['items'][0]['original']]))

    def test_migration_digest_binds_search_policy_without_changing_history(self):
        plan = policy_migration.preview(self.root)
        self.assertEqual(plan['search_mode'], native_search.MODE)
        old = {k: v for k, v in plan.items() if k not in ('search_mode', 'state', 'digest', 'applied')}
        with self.assertRaisesRegex(ValueError, 'preview changed'):
            policy_migration.apply(self.root, digest(old))
        self.assertEqual(self.db.execute('SELECT count(*) FROM policy_transitions').fetchone()[0], 0)
