import json

from x_retention_fixtures import RetentionCase
from x_curator import cycle_store, retention_history


class CycleDiagnosticTests(RetentionCase):
    def test_wiki_failure_survives_finish_and_later_compaction_without_full_report(self):
        identity, _ = cycle_store.begin(self.db, 30)
        result = dict(state='checkpoint', wiki=dict(state='blocked', action='DeadlineExceeded: mapping',
                      pages=['large'] * 10000), report=dict(counts={'published': 2},
                      organization=dict(state='recorded', mapping_eligible=1, mapping_exhausted=10,
                                        mapping_failure_reasons=[dict(action='rejected', sources=10)]),
                      notifications=dict(state='historical_unobserved', unobserved=47,
                                         pending_since_last_observed=0), sources=['large'] * 10000))
        cycle_store.finish(self.db, identity, 'finished', result)
        self.db.execute('UPDATE cycles SET finished=? WHERE id=?', (self.now - 40 * 86400, identity))
        self.db.commit()
        stored = json.loads(self.db.execute('SELECT result FROM cycles').fetchone()[0])
        self.assertEqual(stored['wiki'], dict(state='blocked', action='DeadlineExceeded: mapping'))
        self.assertEqual(stored['report']['organization']['mapping_exhausted'], 10)
        self.assertEqual(stored['report']['notifications']['pending_since_last_observed'], 0)
        self.assertLess(len(json.dumps(stored)), 2000)
        self.assertEqual(retention_history.summary(stored), stored)
        retention_history.run(self.db, apply=True)
        self.assertEqual(json.loads(self.db.execute('SELECT result FROM cycles').fetchone()[0]), stored)
        self.assertEqual(self.db.execute('SELECT state FROM cycles').fetchone()[0], 'finished')
