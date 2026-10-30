"""Unresolved, incomplete and shared diagnostic dependencies must remain intact."""
from x_compact_fixtures import CompactCase
from x_curator import compact_history, compact_seal
from x_curator.row_fingerprint import row_digest
from x_curator.read_set import ChangedDependencies
from x_curator.storage import sha256


class CompactDiagnosticSafetyTests(CompactCase):
    def test_pending_review_attempt_history_is_preserved(self):
        self.old_attempt()
        with self.db:
            self.db.execute("UPDATE attempts SET state='awaiting_review' WHERE token='old-attempt'")
        self.assertEqual(compact_history.run(self.db, self.root, apply=True)['diagnostics']['attempts'], 0)
        self.assertGreater(self.db.execute("SELECT count(*) FROM executions WHERE token='old-attempt' AND log IS NOT NULL").fetchone()[0], 0)

    def test_incomplete_old_executions_are_not_discarded(self):
        self.old_attempt()
        with self.db:
            self.db.execute("UPDATE executions SET finished=NULL WHERE token='old-attempt'")
        self.assertEqual(compact_history.run(self.db, self.root, apply=True)['diagnostics']['attempts'], 0)
        self.assertGreater(self.db.execute("SELECT count(*) FROM executions WHERE token='old-attempt' AND log IS NOT NULL").fetchone()[0], 0)

    def shared_dependency(self):
        self.old_attempt()
        with self.db:
            self.db.execute("UPDATE attempts SET state='awaiting_review' WHERE token='old-attempt'")
        compact_history.run(self.db, self.root, apply=True)
        with self.db:
            self.db.execute("UPDATE attempts SET state='failed' WHERE token='old-attempt'")
        identity = ('publication', self.publication)
        record = compact_seal.read(self.db, self.root, identity)
        query = ("SELECT log FROM executions WHERE token=? ORDER BY id", ('old-attempt',))
        record['queries'][query] = row_digest(self.db.execute(*query))
        with self.db:
            compact_seal.write(self.db, self.root, identity, record, active=1)
        return identity

    def test_controlled_old_history_removal_rebinds_an_unchanged_approval(self):
        identity = self.shared_dependency()
        compact_history.run(self.db, self.root, apply=True)
        self.assertEqual(self.verified()[0], self.packet)
        record = compact_seal.read(self.db, self.root, identity)
        self.assertEqual(len(record['provenance']['transcript_rebindings']), 1)

    def test_preexisting_changed_dependency_rolls_back_removal(self):
        self.shared_dependency()
        with self.db:
            self.db.execute("UPDATE executions SET log=?,log_sha=? WHERE token='old-attempt'", (b'changed', sha256(b'changed')))
        with self.assertRaises(ChangedDependencies):
            compact_history.run(self.db, self.root, apply=True)
        self.assertEqual(self.db.execute("SELECT log FROM executions WHERE token='old-attempt' LIMIT 1").fetchone()[0], b'changed')
