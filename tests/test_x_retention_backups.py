from x_retention_fixtures import RetentionCase
import os
from x_curator import retention


class BackupsRetentionTests(RetentionCase):
    def test_backup_retention_keeps_two_newest_and_skips_uncheckpointed_snapshots(self):
        self.build(1, current=True)
        snapshots = []
        for number in range(4):
            folder = self.root / 'policy-transitions' / str(number)
            folder.mkdir(parents=True)
            path = folder / 'before.sqlite3'
            path.write_bytes(b'forensic snapshot')
            old = self.now - (50 - number) * 86400
            os.utime(path, (old, old))
            snapshots.append(path)
        snapshots[0].with_name('before.sqlite3-wal').write_bytes(b'pending writes')
        retention.run(self.db, self.root, apply=True)
        self.assertTrue(snapshots[0].exists())
        self.assertFalse(snapshots[1].exists())
        self.assertTrue(all(p.exists() for p in snapshots[2:]))
