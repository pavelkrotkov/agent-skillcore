from x_retention_fixtures import RetentionCase
import json
from x_curator import retention


class WikiRetentionTests(RetentionCase):
    def test_preview_is_read_only_and_apply_keeps_active_and_two_previous(self):
        # A rollback can make the active generation older than both retained predecessors.
        builds = [self.build(i, current=i == 3) for i in range(1, 7)]
        before = self.db.total_changes
        files_before = {str(p.relative_to(self.root)) for p in self.root.rglob('*')}
        result = retention.run(self.db, self.root)
        self.assertEqual(result['state'], 'preview')
        self.assertEqual(self.db.total_changes, before)
        self.assertEqual({str(p.relative_to(self.root)) for p in self.root.rglob('*')}, files_before)
        self.assertTrue(all(p.exists() for p in builds))
        retention.run(self.db, self.root, apply=True)
        self.assertEqual({p.name for p in builds if p.exists()}, {f'{3:064x}', f'{5:064x}', f'{6:064x}'})
        self.assertEqual(self.db.execute('SELECT count(*) FROM wiki_builds').fetchone()[0], 3)
        self.assertEqual(json.loads((self.root / 'wiki/CURRENT.json').read_text())['generation'], f'{3:064x}')

    def test_missing_build_records_and_old_orphans_are_collected_but_recent_orphans_stay(self):
        missing = self.build(1)
        import shutil
        shutil.rmtree(missing)
        self.build(2, current=True)
        old = self.root / 'wiki/builds' / ('a' * 64)
        old.mkdir()
        self.age(old)
        recent = self.root / 'wiki/builds' / ('b' * 64)
        recent.mkdir()
        retention.run(self.db, self.root, apply=True)
        self.assertFalse(old.exists())
        self.assertTrue(recent.exists())
        self.assertIsNone(self.db.execute('SELECT id FROM wiki_builds WHERE id=?', (f'{1:064x}',)).fetchone())

    def test_damaged_active_build_blocks_cleanup(self):
        old = self.build(1)
        current = self.build(2, current=True)
        (current / 'site/index.html').write_bytes(b'corrupt')
        with self.assertRaisesRegex(ValueError, 'current wiki'):
            retention.run(self.db, self.root, apply=True)
        self.assertTrue(old.exists())
