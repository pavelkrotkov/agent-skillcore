"""Authentication is required before decoding or discarding model-history copies."""
from pathlib import Path
import json
import os
import sqlite3
import tempfile
import time
import unittest
from unittest.mock import patch

from x_fixtures import SCRIPTS
from x_curator import compact_seal, compact_artifacts, compact_codec
from x_curator.proof_mode import MaintenanceRequired


from x_compact_artifact_fixtures import ArtifactCase


class CompactArtifactTests(ArtifactCase):

    def test_changed_bytes_fail_before_the_record_is_decoded(self):
        self.db.execute("UPDATE compact_approvals SET body=X'00'")
        with self.assertRaisesRegex(MaintenanceRequired, 'signature'):
            compact_seal.read(self.db, self.root, self.identity)

    def test_copying_a_seal_to_another_identity_cannot_authorize_it(self):
        self.db.execute("UPDATE compact_approvals SET identity='another-publication'")
        with self.assertRaisesRegex(MaintenanceRequired, 'signature'):
            compact_seal.read(self.db, self.root, ('publication', 'another-publication'))

    def test_optional_memo_deletion_does_not_delete_canonical_approval(self):
        self.assertEqual(compact_seal.read(self.db, self.root, self.identity), self.record)
        self.assertEqual(list((self.root / 'audit-memos').glob('*.memo')), [])

    def test_only_the_closed_identified_session_is_removed(self):
        identity = '12345678-1234-1234-1234-123456789abc'
        path = self.session_file(identity)
        with patch.dict(os.environ, CODEX_HOME=str(self.root / 'worker')):
            result = compact_artifacts.run(self.db, self.root)
        self.assertEqual(result['files'], 1)
        self.assertFalse(path.exists())

    def test_relabelled_foreign_session_is_preserved(self):
        identity = '12345678-1234-1234-1234-123456789abc'
        path = self.session_file(identity, observed='different-session')
        with patch.dict(os.environ, CODEX_HOME=str(self.root / 'worker')):
            self.assertEqual(compact_artifacts.run(self.db, self.root)['files'], 0)
        self.assertTrue(path.exists())
