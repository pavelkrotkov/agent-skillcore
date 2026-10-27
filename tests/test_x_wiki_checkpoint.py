"""Routine indexing reuses accepted knowledge and still withdraws changed evidence."""
import json
import os
from unittest.mock import patch
from x_wiki_fixtures import WikiCase
from x_curator import wiki,publication_audit,proof_mode


class WikiCheckpointTests(WikiCase):
    def setUp(self):
        super().setUp()
        self.db.executescript('CREATE TABLE unrelated_progress(value INTEGER); INSERT INTO unrelated_progress VALUES (0);')
        with patch('x_curator.wiki_mapping.runner',return_value=self.model):
            self.expected=wiki.run(self.db,self.root)

    def test_unchanged_run_does_not_reload_proofs_or_render(self):
        with patch('x_curator.wiki_inputs.sources',side_effect=AssertionError('history reload')):
            with patch('x_curator.wiki_build.render',side_effect=AssertionError('render')):
                self.assertEqual(wiki.run(self.db,self.root,0),self.expected)

    def test_unrelated_row_change_preserves_verified_publications(self):
        self.db.execute('UPDATE unrelated_progress SET value=1')
        self.db.commit()
        with patch.object(publication_audit,'validate_approval',side_effect=AssertionError('proof replay')):
            with patch('x_curator.wiki_build.render',side_effect=AssertionError('render')):
                self.assertEqual(wiki.run(self.db,self.root,0),self.expected)

    def test_changed_approval_withdraws_active_wiki(self):
        self.db.execute("UPDATE executions SET output='changed' WHERE role='review'")
        self.db.commit()
        with self.assertRaises(ValueError):
            wiki.run(self.db,self.root,0)
        self.assertIsNone(json.loads((self.root/'wiki/CURRENT.json').read_text())['generation'])

    def test_same_size_restored_mtime_source_change_cannot_use_checkpoint(self):
        path=self.root/self.db.execute('SELECT path FROM publications').fetchone()[0]
        before=path.stat()
        path.write_bytes(b'!'+path.read_bytes()[1:])
        os.utime(path,ns=(before.st_atime_ns,before.st_mtime_ns))
        with self.assertRaises(ValueError):
            wiki.run(self.db,self.root,0)
        self.assertIsNone(json.loads((self.root/'wiki/CURRENT.json').read_text())['generation'])

    def test_explicit_audit_replays_approvals(self):
        with patch.object(publication_audit,'validate_approval',wraps=publication_audit.validate_approval) as verify:
            with proof_mode.audit():
                self.assertEqual(wiki.run(self.db,self.root,0),self.expected)
        self.assertGreater(verify.call_count,0)
