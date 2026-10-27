import json

from x_batch_fixtures import BatchCase
from x_fixtures import Client
from x_curator import batch_report
from x_curator.storage import open_store


class BatchReuseTests(BatchCase):
    def capture(self, source):
        rows = self.db.execute('''SELECT c.payload FROM captures c JOIN attempts a ON a.token=c.token
            WHERE a.account=? AND a.id=?''', (Client.account, source))
        return next(payload for row in rows if (payload := json.loads(row[0])).get('quick_excerpt'))

    def test_restart_reuses_shared_body_and_isolates_failed_member(self):
        self.add_items(3)
        original = self.checker
        def mixed(request):
            if request['bundle']['source'] == '2':
                raise OSError('Synthetic model transport interruption')
            return original(request)
        self.checker = mixed
        self.assertEqual(self.run_batch(limit=2)['attempted'], 2)
        self.db.close()
        self.db = open_store(self.root)
        self.assertEqual(self.run_batch()['attempted'], 1)
        batch = batch_report.report(self.db)['batches'][0]
        self.assertEqual(batch['counts'], {'supported': 2, 'failed_processing': 1})
        first, last = self.capture('1'), self.capture('3')
        self.assertEqual((first['body_sha'], first['fetched']), (last['body_sha'], last['fetched']))
        self.assertIn('reused_from', last)
        self.assertEqual(sum('format=rss' not in url for url in self.calls), 1)
        history = self.db.execute('''SELECT (SELECT count(*) FROM attempts),
            (SELECT count(*) FROM quick_checks),(SELECT count(*) FROM retrievals)''').fetchone()
        self.db.close()
        self.db = open_store(self.root)
        self.assertEqual(self.run_batch()['attempted'], 0)
        self.assertEqual(self.db.execute('''SELECT (SELECT count(*) FROM attempts),
            (SELECT count(*) FROM quick_checks),(SELECT count(*) FROM retrievals)''').fetchone(), history)
        self.assertEqual(self.db.execute('SELECT count(*) FROM publications').fetchone()[0], 2)
