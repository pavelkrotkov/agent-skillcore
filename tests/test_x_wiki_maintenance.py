"""Maintenance requirements preserve accepted source history and never silently replay it."""
from unittest.mock import patch
from x_wiki_fixtures import WikiCase
from x_curator import wiki,publication_audit,proof_mode,audit_memo,audit_reuse


class WikiMaintenanceTests(WikiCase):
    def setUp(self):
        super().setUp()
        with patch('x_curator.wiki_mapping.runner',return_value=self.model):
            self.expected=wiki.run(self.db,self.root)

    def test_missing_historical_seals_require_explicit_audit_on_repeated_runs(self):
        for identity in (('publication',self.publication),('wiki-checkpoint',0)):
            audit_memo.target(self.root,identity)[0].unlink()
        audit_reuse._CACHE.clear()
        with patch.object(publication_audit,'validate_approval',side_effect=AssertionError('hidden archive replay')):
            for _ in range(2):
                with self.assertRaisesRegex(proof_mode.MaintenanceRequired,'Historical proof checkpoint'):
                    wiki.run(self.db,self.root,0)
        with proof_mode.audit():
            self.assertEqual(wiki.run(self.db,self.root,0),self.expected)

    def test_missing_historical_seal_does_not_invalidate_accepted_publication(self):
        audit_memo.target(self.root,('publication',self.publication))[0].unlink()
        audit_reuse._CACHE.clear()
        with self.assertRaises(proof_mode.MaintenanceRequired):
            publication_audit.audit(self.db,self.root)
        self.assertEqual(self.db.execute('SELECT state FROM publications').fetchone()[0],'published')
        self.assertEqual(self.db.execute('SELECT count(*) FROM publication_audit_failures').fetchone()[0],0)

    def test_optional_checkpoint_write_failure_preserves_successful_generation(self):
        audit_memo.target(self.root,('wiki-checkpoint',0))[0].unlink()
        with patch('x_curator.audit_memo.write',side_effect=OSError('cache storage unavailable')):
            result=wiki.run(self.db,self.root,0)
        self.assertEqual(result['generation'],self.expected['generation'])
        self.assertEqual(result['verified_sources'],1)
