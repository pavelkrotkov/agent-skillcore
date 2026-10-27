from x_retention_fixtures import RetentionCase
import json
from x_curator import cycle_store, retention


class HistoryRetentionTests(RetentionCase):
    def test_cycle_storage_is_compact_and_preserves_dependency_diagnostics(self):
        identity, _ = cycle_store.begin(self.db, 30)
        result = dict(state='checkpoint', work=dict(dependency={'ready': False}, items=['large'] * 10000),
                      report=dict(selected_sources=2, counts={'published': 2}, sources=['large'] * 10000,
                                  wiki={'manifest': {'generation': 'current', 'files': ['large'] * 10000}}))
        cycle_store.finish(self.db, identity, 'finished', result)
        stored = self.db.execute('SELECT result FROM cycles').fetchone()[0]
        self.assertLess(len(stored), 2000)
        self.assertEqual(json.loads(stored)['work']['dependency'], {'ready': False})
        self.assertEqual(len(result['report']['sources']), 10000)

    def test_historical_cycle_compaction_preserves_rows_and_attempt_budgets(self):
        self.build(1, current=True)
        identity, _ = cycle_store.begin(self.db, 30)
        result = dict(state='checkpoint', report=dict(counts={'published': 1}, sources=['large'] * 1000))
        self.db.execute('UPDATE cycles SET finished=?,result=? WHERE id=?',
                        (self.now - 40 * 86400, json.dumps(result), identity))
        self.db.commit()
        preview = retention.run(self.db, self.root)
        self.assertGreater(preview['history']['bytes'], 0)
        self.assertEqual(json.loads(self.db.execute('SELECT result FROM cycles').fetchone()[0]), result)
        retention.run(self.db, self.root, apply=True)
        stored = json.loads(self.db.execute('SELECT result FROM cycles').fetchone()[0])
        self.assertEqual(stored['report']['counts'], {'published': 1})
        self.assertNotIn('sources', stored['report'])
