import time
from unittest.mock import patch

from x_fixtures import Client, CollectionCase, envelope, response
from x_lock_fixtures import contend
from x_curator import cycle_stages
from x_curator.command_lock import lockfile
from x_curator.supervisor import run


class WikiLockContentionTests(CollectionCase):
    def cycle(self):
        bookmarks = envelope([{'type': 'TimelineAddEntries', 'entries': []}], 'bookmarks')
        client = Client([(200, response(['1'])), (200, bookmarks)])
        with patch('x_curator.intake.time.sleep'):
            return run(self.db, self.root, client, 0, 0, 1)

    def test_wiki_and_report_wait_for_index_release(self):
        for module in ('cycle_stages', 'accounting'):
            with self.subTest(module=module), contend(self.root, module, 0.2):
                started = time.monotonic()
                result = self.cycle()
                elapsed = time.monotonic() - started
                self.assertGreaterEqual(elapsed, 0.2)
                self.assertEqual(result['state'], 'checkpoint')
                row = self.db.execute('SELECT state FROM cycles ORDER BY started DESC LIMIT 1').fetchone()
                self.assertEqual(row['state'], 'finished')

    def test_wait_at_either_acquisition_keeps_original_deadline(self):
        for module, stage in (('cycle_stages', 'wiki'), ('accounting', 'reconciled')):
            with self.subTest(module=module), contend(self.root, module, 30):
                started = time.monotonic()
                result = self.cycle()
                self.assertLess(time.monotonic() - started, 3)
                self.assertIn('DeadlineExceeded', result['action'])
                row = self.db.execute('SELECT * FROM cycles ORDER BY started DESC LIMIT 1').fetchone()
                self.assertEqual((row['state'], row['stage']), ('failed', stage))
                self.assertEqual(row['deadline'] - row['started'], 1)
            with lockfile(self.root, '.wiki.lock'):
                pass

    def test_organizer_remains_exclusive_while_supervisor_owns_lock(self):
        original = cycle_stages.organize
        def organize(*args):
            with self.assertRaises(BlockingIOError):
                with lockfile(self.root, '.wiki.lock'):
                    self.fail('overlapping index')
            return original(*args)
        with patch('x_curator.cycle_stages.organize', organize):
            self.assertEqual(self.cycle()['state'], 'checkpoint')
