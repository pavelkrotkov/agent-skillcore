import json
import sqlite3
from contextlib import contextmanager
from unittest.mock import patch

from x_wiki_fixtures import WikiCase
from x_curator import wiki_inputs
from x_curator.read_set import ChangedDependencies
from x_curator.wiki import run


class WikiConcurrencyTests(WikiCase):
    @contextmanager
    def concurrent_write(self, sql):
        original = wiki_inputs.sources
        other = sqlite3.connect(self.root / 'curator.sqlite3', timeout=0.05)
        def sources(db, root, publications=None):
            result = original(db, root, publications)
            if self.db.in_transaction:
                with other:
                    other.execute(sql)
            return result
        try:
            with patch('x_curator.wiki_mapping.runner', return_value=self.model), patch('x_curator.wiki_commit.wiki_inputs.sources', side_effect=sources):
                yield
        finally:
            other.close()

    def test_unrelated_writer_proceeds_during_audit_without_preventing_activation(self):
        self.db.execute('CREATE TABLE unrelated_progress (value INTEGER)')
        with self.concurrent_write('INSERT INTO unrelated_progress VALUES (1)'):
            report = run(self.db, self.root)
        self.assertGreaterEqual(self.db.execute('SELECT count(*) FROM unrelated_progress').fetchone()[0], 1)
        self.assertEqual(report['mapped_sources'], 1)
        self.assertEqual(json.loads((self.root / 'wiki/CURRENT.json').read_text())['generation'], report['generation'])
        with patch('x_curator.wiki_mapping.runner') as model:
            self.assertEqual(run(self.db, self.root), report)
        model.assert_not_called()

    def reject_change(self, sql):
        with self.concurrent_write(sql), self.assertRaises(ChangedDependencies):
            run(self.db, self.root)
        self.assertFalse(self.db.in_transaction)
        self.assertFalse((self.root / 'wiki/CURRENT.json').exists())
        self.assertEqual(self.db.execute('SELECT count(*) FROM wiki_builds').fetchone()[0], 0)

    def test_source_withdrawal_during_audit_cannot_activate_stale_generation(self):
        self.reject_change("UPDATE publications SET state='invalid'")
        with patch('x_curator.wiki_mapping.runner') as model:
            self.assertEqual(run(self.db, self.root), {'state': 'empty', 'sources': 0})
        model.assert_not_called()

    def test_job_eligibility_change_prevents_activation(self):
        self.reject_change("UPDATE jobs SET state='needs_action'")

    def test_mapping_change_preserves_source_fallback(self):
        with self.concurrent_write("UPDATE wiki_runs SET state='failed'"), self.assertRaises(ChangedDependencies):
            run(self.db, self.root)
        self.assertTrue((self.root / 'wiki/CURRENT.json').exists())

    def test_approval_change_prevents_activation(self):
        self.reject_change("UPDATE executions SET output='changed' WHERE role='review'")
