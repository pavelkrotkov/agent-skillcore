from x_repair_fixtures import QualificationCase
import sqlite3
from unittest.mock import patch

import repair_manifest
import repair_dispatch
import repair_eligibility
import repair_qualification
from x_curator import quick_store
from x_fixtures import Client

class QualificationTests(QualificationCase):
    def test_preview_is_read_only_and_stale_scope_or_history_rolls_back_all_grants(self):
        manifest = self.manifest()
        with sqlite3.connect((self.root / 'curator.sqlite3').as_uri() + '?mode=ro', uri=True) as db:
            db.row_factory = sqlite3.Row
            self.assertEqual(repair_qualification.prepare(db, manifest)['state'], 'preview')
            self.assertEqual(db.total_changes, 0)
        approval = repair_manifest.identity(manifest)
        with self.db:
            self.db.execute("UPDATE quick_tools SET output='{}'")
        with self.assertRaisesRegex(ValueError, 'history changed'):
            repair_qualification.prepare(self.db, manifest, approval)
        self.assertEqual(self.db.execute('SELECT count(*) FROM quick_recoveries').fetchone()[0], 0)
        manifest['items'].append(manifest['items'][0])
        with self.assertRaises(ValueError):
            repair_qualification.prepare(self.db, manifest, approval)

    def test_grant_reapply_and_crash_after_claim_do_not_create_another_attempt(self):
        manifest = self.manifest()
        item = manifest['items'][0]
        original = dict(self.db.execute('SELECT * FROM quick_checks').fetchone())
        approval = repair_manifest.identity(manifest)
        repair_qualification.prepare(self.db, manifest, approval)
        repair_qualification.prepare(self.db, manifest, approval)
        self.assertEqual(self.db.execute('SELECT count(*) FROM recovery_grants').fetchone()[0], 1)
        first = repair_dispatch.claim(self.db, item, approval)
        self.assertIsNone(repair_dispatch.claim(self.db, item, approval))
        self.assertEqual(first['attempts'], item['attempts'] + 1)
        self.assertEqual(dict(self.db.execute('SELECT * FROM quick_checks WHERE id=?', (original['id'],)).fetchone()), original)
        check = quick_store.start(self.db, first['token'], first['lease_until'] - 180)
        self.assertEqual(check['deadline'] - check['started'], 120)
        self.assertNotEqual(check['id'], original['id'])
