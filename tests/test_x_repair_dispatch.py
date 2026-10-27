from x_repair_fixtures import QualificationCase
from unittest.mock import patch

from x_native_search_fixtures import NativeCase
import repair_manifest
import repair_dispatch
import repair_eligibility
from x_fixtures import Client

class QualificationDispatchTests(QualificationCase, NativeCase):
    def test_only_selected_item_runs_and_unrelated_pending_jobs_stay_untouched(self):
        manifest = self.manifest()
        self.add_items(3)
        outside = [dict(row) for row in self.db.execute("SELECT * FROM jobs WHERE id!='1' ORDER BY id")]
        approval = repair_manifest.identity(manifest)
        self.checker = super().checker
        with patch('x_curator.quick_web.fetch', self.fetch), patch('x_curator.quick_search.fetch', self.fetch), \
                patch('x_curator.quick_process.runner', self.model), \
                patch('x_curator.research.research', side_effect=AssertionError('deep work forbidden')):
            result = repair_dispatch.run(self.db, self.root, Client([]), manifest, approval)
        item = result['results'][0]
        self.assertEqual((item['state'], item['outcome'], item['disposition']), ('published', 'supported', 'supported'))
        self.assertEqual((item['metrics']['searches'], item['metrics']['model_calls'], item['metrics']['deadline_met']), (4, 1, True))
        self.assertEqual(item['metrics']['queries'], ['synthetic release ' + str(i) for i in range(4)])
        self.assertTrue(item['metrics']['tools'])
        self.assertEqual(result['wiki']['verified_sources'], 1)
        self.assertGreaterEqual(result['wiki']['verdict_to_index_seconds'], 0)
        self.assertEqual([dict(row) for row in self.db.execute("SELECT * FROM jobs WHERE id!='1' ORDER BY id")], outside)
        checks = self.db.execute('SELECT * FROM quick_checks ORDER BY started').fetchall()
        self.assertEqual(len(checks), 2)
        self.assertEqual(checks[-1]['searches'], 4)

    def test_provider_capacity_and_post_grant_state_changes_prevent_claim(self):
        manifest = self.manifest()
        approval = repair_manifest.identity(manifest)
        with patch('x_curator.provider_health.blocked', return_value={'action': 'provider unavailable'}):
            result = repair_dispatch.run(self.db, self.root, Client([]), manifest, approval)
        self.assertEqual(result['state'], 'blocked')
        self.assertEqual(repair_eligibility.job(self.db, manifest['items'][0])['attempts'], manifest['items'][0]['attempts'])
        with patch('x_curator.worker_capacity.available', return_value=False):
            with self.assertRaisesRegex(ValueError, 'free source-worker slot'):
                repair_dispatch.claim(self.db, manifest['items'][0], approval)
        with self.db:
            self.db.execute("UPDATE jobs SET state='excluded'")
        with self.assertRaisesRegex(ValueError, 'job changed'):
            repair_dispatch.claim(self.db, manifest['items'][0], approval)
