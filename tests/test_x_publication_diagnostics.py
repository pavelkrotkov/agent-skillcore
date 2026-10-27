import io
import json
from types import SimpleNamespace
from unittest.mock import patch

from x_publication_fixtures import PublicationCase
from x_curator import __main__, publication_audit, publication_diagnostics
from x_curator.publication import publish


class PublicationDiagnosticsTests(PublicationCase):
    def test_withdrawal_retains_error_and_read_only_recheck_never_restores(self):
        identity = publish(self.db, self.root, self.token, *self.approved_executions())
        original = dict(self.db.execute('SELECT * FROM jobs').fetchone())
        for message in ('temporary verifier failure', 'second failure'):
            with self.db:
                self.db.execute("UPDATE publications SET state='published'")
            with patch('x_curator.publication_audit.verify_publication', side_effect=ValueError(message)):
                self.assertEqual(publication_audit.audit(self.db, self.root), [identity])
        before = '\n'.join(self.db.iterdump())
        args = SimpleNamespace(command='diagnose-publication', state=self.root, publication=identity)
        with patch('x_curator.__main__.arguments', return_value=args), patch('x_curator.__main__.open_store', side_effect=AssertionError('read only')), patch('sys.stdout', new_callable=io.StringIO) as output:
            self.assertEqual(__main__.main(), 0)
        result = json.loads(output.getvalue())
        self.assertTrue(result['verified'])
        self.assertEqual(result['state'], 'invalid')
        self.assertEqual([r['error'].partition('; ')[2] for r in result['failures']],
                         ['ValueError: temporary verifier failure', 'ValueError: second failure'])
        self.assertTrue(all(r['error'].startswith('pid=') and 'code=' in r['error'] for r in result['failures']))
        self.assertTrue(all(r['created'] > 0 for r in result['failures']))
        self.assertEqual('\n'.join(self.db.iterdump()), before)
        job = dict(self.db.execute('SELECT * FROM jobs').fetchone())
        self.assertEqual((job['attempts'], job['max_attempts']), (original['attempts'], original['max_attempts']))

    def test_targeted_recheck_reports_real_failure_and_supports_legacy_schema(self):
        identity = publish(self.db, self.root, self.token, *self.approved_executions())
        row = self.db.execute('SELECT * FROM publications').fetchone()
        (self.root / row['path']).write_bytes(b'tampered')
        self.db.execute('DROP TABLE publication_audit_failures')
        self.db.commit()
        before = '\n'.join(self.db.iterdump())
        result = publication_diagnostics.diagnose(self.root, identity)
        self.assertFalse(result['verified'])
        self.assertIn('differs from verified evidence', result['error'])
        self.assertEqual(result['failures'], [])
        self.assertEqual(result['state'], 'published')
        self.assertEqual('\n'.join(self.db.iterdump()), before)
