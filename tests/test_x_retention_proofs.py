"""Missing or edited canonical proof material must prevent destructive cache cleanup."""
from x_retention_run_fixtures import RunRetentionCase
import json
import os
from unittest.mock import patch
from x_curator import retention


class ProofRetentionTests(RunRetentionCase):
    def test_missing_accepted_mapping_seal_preserves_old_memos(self):
        self.build(1, current=True)
        folder = self.root / 'audit-memos'
        folder.mkdir()
        stale = folder / ('a' * 64 + '.memo')
        stale.write_bytes(b'old mapping proof')
        self.age(stale)
        self.db.execute('INSERT INTO wiki_runs VALUES (?,?,?,?,?,?,NULL,NULL,NULL)',
                        ('mapping', '{}', 'hash', 0, 1, 'accepted'))
        self.db.commit()
        result = retention.run(self.db, self.root, apply=True)
        self.assertIn('action', result['memos'])
        self.assertTrue(stale.exists())

    def test_changed_canonical_log_cannot_authorize_deleting_native_copies(self):
        self.build(1, current=True)
        copied, _, transcript, original, _ = self.attempt()
        self.db.execute('UPDATE executions SET log=?', (json.dumps({'changed': True}).encode(),))
        self.db.commit()
        with patch.dict(os.environ, CODEX_HOME=str(self.root / 'worker')):
            retention.run(self.db, self.root, apply=True)
        self.assertTrue(copied.exists())
        self.assertTrue(transcript.exists())
        self.assertTrue(original.exists())
