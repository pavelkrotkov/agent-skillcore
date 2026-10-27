import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

from x_publication_fixtures import PublicationCase
from x_fixtures import SCRIPTS
from x_curator.publication import publish
from x_curator import audit_reuse, audit_memo, publication_audit, wiki_inputs, proof_revisions


class RestartAuditTests(PublicationCase):
    def setUp(self):
        super().setUp()
        proposal, review = self.approved_executions()
        self.publication = publish(self.db, self.root, self.token, proposal, review)
        proof_revisions.prepare(self.db)
        self.sources = wiki_inputs.sources(self.db, self.root)

    def test_fresh_process_reuses_proof_without_factory_replay(self):
        script = "from pathlib import Path; import sqlite3; from unittest.mock import patch; from x_curator import wiki_inputs,publication_audit; root=Path(__import__('sys').argv[1]); db=sqlite3.connect('file:'+str(root/'curator.sqlite3')+'?mode=ro',uri=True); db.row_factory=sqlite3.Row; guard=patch.object(publication_audit,'validate_approval',side_effect=AssertionError('full proof replay')); guard.start(); assert len(wiki_inputs.sources(db,root))==1"
        environment = dict(os.environ, PYTHONPATH=str(SCRIPTS) + os.pathsep + os.environ.get('PYTHONPATH', ''))
        result = subprocess.run([sys.executable, '-c', script, str(self.root)], capture_output=True, env=environment)
        self.assertEqual(result.returncode, 0, result.stderr.decode())

    def test_unsigned_memo_never_reaches_deserialization(self):
        path, _ = audit_memo.target(self.root, ('publication', self.publication))
        body = path.read_bytes()
        path.write_bytes(b'!' + body[1:])
        audit_reuse._CACHE.clear()
        with patch('x_curator.audit_seal.loads', side_effect=AssertionError('untrusted deserialize')):
            self.assertEqual(wiki_inputs.sources(self.db, self.root), self.sources)

    def test_changed_approval_is_rejected_after_restart(self):
        audit_reuse._CACHE.clear()
        self.db.execute("UPDATE executions SET output='changed' WHERE role='review'")
        with self.assertRaises(ValueError):
            wiki_inputs.sources(self.db, self.root)

    def test_code_policy_change_requires_full_proof(self):
        audit_reuse._CACHE.clear()
        with patch('x_curator.audit_seal.policy', return_value='changed-code-policy'), patch.object(publication_audit, 'validate_approval', wraps=publication_audit.validate_approval) as proof:
            self.assertEqual(wiki_inputs.sources(self.db, self.root), self.sources)
        self.assertEqual(proof.call_count, 1)

    def test_restart_rejects_same_size_same_mtime_file_tampering(self):
        path = self.root / self.db.execute('SELECT path FROM publications WHERE id=?', (self.publication,)).fetchone()[0]
        stamp = path.stat()
        body = path.read_bytes()
        path.write_bytes(b'!' + body[1:])
        os.utime(path, ns=(stamp.st_atime_ns, stamp.st_mtime_ns))
        audit_reuse._CACHE.clear()
        with self.assertRaisesRegex(ValueError, 'verified evidence'):
            wiki_inputs.sources(self.db, self.root)
