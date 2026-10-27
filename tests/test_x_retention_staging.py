from x_retention_run_fixtures import RunRetentionCase
import os
from unittest.mock import patch
from x_curator import retention


class StagingRetentionTests(RunRetentionCase):
    def test_only_exact_finished_staging_copies_expire_and_canonical_evidence_stays(self):
        self.build(1, current=True)
        copied, image, transcript, original, log = self.attempt()
        with patch.dict(os.environ, CODEX_HOME=str(self.root / 'worker')):
            retention.run(self.db, self.root)
            self.assertTrue(copied.exists())
            retention.run(self.db, self.root, apply=True)
        self.assertFalse(copied.exists())
        self.assertFalse(image.exists())
        self.assertFalse(transcript.exists())
        self.assertEqual(original.read_bytes(), b'original image')
        self.assertEqual(self.db.execute('SELECT log FROM executions').fetchone()[0], log)

    def test_active_run_and_unique_staging_bytes_are_preserved(self):
        self.build(1, current=True)
        copied, image, transcript, _, _ = self.attempt(active=True)
        with patch.dict(os.environ, CODEX_HOME=str(self.root / 'worker')):
            retention.run(self.db, self.root, apply=True)
        self.assertTrue(all(p.exists() for p in (copied, image, transcript)))
        self.db.execute("UPDATE attempts SET finished=?,state='published'", (self.now - 40 * 86400,))
        self.db.execute("UPDATE jobs SET state='published'")
        self.db.commit()
        copied.write_text('unique unrecorded event')
        image.write_bytes(b'changed image!')
        transcript.write_text('unique native transcript')
        for path in (copied, image, transcript):
            self.age(path)
        with patch.dict(os.environ, CODEX_HOME=str(self.root / 'worker')):
            retention.run(self.db, self.root, apply=True)
        self.assertTrue(all(p.exists() for p in (copied, image, transcript)))
