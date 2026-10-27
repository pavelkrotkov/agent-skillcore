import json
from unittest.mock import patch

from x_publication_fixtures import PublicationCase
from x_curator.worker_process import process


class FailureRecordTests(PublicationCase):
    def test_worker_retains_private_sqlite_code_and_originating_traceback(self):
        job = dict(self.db.execute('SELECT * FROM jobs').fetchone())
        def broken_publication(*args):
            self.db.execute('SELECT * FROM missing_synthetic_table')
        with patch('x_curator.worker_process.research', side_effect=broken_publication):
            result = process(self.db, self.root, None, job)
        self.assertIn('SQLITE_ERROR', result['action'])
        paths = list((self.root / 'failures').glob('*.json'))
        self.assertEqual(len(paths), 1)
        record = json.loads(paths[0].read_text())
        self.assertEqual(record['sqlite_errorcode'], 1)
        self.assertEqual(record['token'], self.token)
        self.assertIn('broken_publication', record['traceback'])
        self.assertEqual(paths[0].stat().st_mode & 0o777, 0o600)
