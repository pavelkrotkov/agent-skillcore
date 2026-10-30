"""Superseded diagnostics retain provenance without granting approval or recovery."""
from x_compact_fixtures import CompactCase
from x_curator import compact_history, compact_seal, compact_proofs


class CompactDiagnosticTests(CompactCase):
    def test_verified_job_can_discard_closed_failed_history_without_approving_it(self):
        self.old_attempt()
        before = [tuple(r) for r in self.db.execute('SELECT * FROM attempts ORDER BY token')]
        result = compact_history.run(self.db, self.root, apply=True)
        self.assertEqual(result['diagnostics']['attempts'], 1)
        self.assertEqual(self.db.execute("SELECT count(*) FROM executions WHERE token='old-attempt' AND log IS NOT NULL").fetchone()[0], 0)
        identity = ('diagnostic', 'old-attempt')
        self.assertEqual(compact_seal.read(self.db, self.root, identity)['type'], 'superseded-diagnostic/v1')
        self.assertIsNone(compact_proofs.restored(self.db, self.root, identity))
        self.assertEqual(before, [tuple(r) for r in self.db.execute('SELECT * FROM attempts ORDER BY token')])
        self.assertEqual(self.verified()[0], self.packet)

    def test_corrupt_superseded_history_is_preserved(self):
        self.old_attempt()
        with self.db:
            self.db.execute("UPDATE executions SET log=X'00' WHERE token='old-attempt'")
        result = compact_history.run(self.db, self.root, apply=True)
        self.assertEqual(result['diagnostics']['attempts'], 0)
        self.assertEqual(self.db.execute("SELECT log FROM executions WHERE token='old-attempt' LIMIT 1").fetchone()[0], b'\x00')

    def test_history_referenced_by_any_publication_is_preserved(self):
        self.old_attempt()
        with self.db:
            self.db.execute('''INSERT INTO publications SELECT id||'-old',account,source,
                proposal||'-old',review||'-old',path||'-old',body,sha,'invalid',created FROM publications''')
        result = compact_history.run(self.db, self.root, apply=True)
        self.assertEqual(result['diagnostics']['attempts'], 0)
        self.assertGreater(self.db.execute("SELECT count(*) FROM executions WHERE token='old-attempt' AND log IS NOT NULL").fetchone()[0], 0)
