"""Compact approval migration regression checks."""
from unittest.mock import patch
from x_compact_fixtures import CompactCase
from x_curator import compact_history, audit_reuse, compact_seal, wiki_inputs
from x_curator.publication_audit import audit as audit_publications
from x_curator.proof_mode import MaintenanceRequired, audit


class CompactpreservationTests(CompactCase):
    def test_unrelated_job_scheduling_changes_do_not_require_model_history(self):
        compact_history.run(self.db, self.root, apply=True)
        with self.db:
            self.db.execute("UPDATE jobs SET next_at=next_at+10,action='operator schedule update'")
        self.assertEqual(self.verified()[0], self.packet)


    def test_invalid_original_proof_rolls_back_without_purging_any_history(self):
        with self.db:
            self.db.execute("UPDATE executions SET log=X'00'")
        before = [tuple(r) for r in self.db.execute('SELECT id,log FROM executions ORDER BY id')]
        with self.assertRaises((ValueError, UnicodeError)):
            compact_history.run(self.db, self.root, apply=True)
        self.assertEqual(before, [tuple(r) for r in self.db.execute('SELECT id,log FROM executions ORDER BY id')])
        self.assertEqual(self.db.execute('SELECT count(*) FROM compact_approvals').fetchone()[0], 0)


    def test_failed_mappings_and_running_execution_history_remain_available(self):
        with self.db:
            self.db.execute('''INSERT INTO wiki_runs SELECT id||'-failed',input,input_sha,
                started,expires,'failed',proposal,review,'synthetic rejected history'
                FROM wiki_runs WHERE state='accepted' ''')
            self.db.execute("INSERT INTO executions(id,token,role,model,input,input_sha,started,log) VALUES ('active',?,'synthetic_active','synthetic','{}','sha',0,X'01')", (self.token,))
        compact_history.run(self.db, self.root, apply=True)
        self.assertEqual(self.db.execute("SELECT log FROM executions WHERE id='active'").fetchone()[0], b'\x01')
        self.assertIsNotNone(self.db.execute("SELECT proposal FROM wiki_runs WHERE state='failed'").fetchone()[0])
