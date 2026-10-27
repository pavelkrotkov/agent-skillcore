import json
from unittest.mock import patch

from x_fixtures import Client, CollectionCase, response, envelope
from x_curator.supervisor import run
from x_curator import cycle_store, stage_timings
from x_curator.process_liveness import state
from x_curator.command_lock import lockfile


class SupervisorTests(CollectionCase):
    def test_bounded_cycle_collects_new_sources_and_accounts_for_unfinished_work(self):
        bookmarks = envelope([{'type': 'TimelineAddEntries', 'entries': []}], 'bookmarks')
        with patch('x_curator.intake.time.sleep'):
            result = run(self.db, self.root, Client([(200, response(['1'])), (200, bookmarks)]), 0, 0, 30)
        self.assertEqual(result['state'], 'checkpoint')
        self.assertEqual(result['report']['counts'], {'pending': 1})
        source = result['report']['sources'][0]
        self.assertEqual((source['publications'], source['action']), (0, 'bounded quick fact-check'))
        row = dict(self.db.execute('SELECT * FROM cycles').fetchone())
        self.assertEqual((row['state'], state(row)), ('finished', 'finished'))
        self.assertEqual(json.loads(row['result'])['cycle'], result['cycle'])
        stages = stage_timings.report(self.db)['aggregates']
        self.assertEqual(stages['cycle.run']['outcomes']['completed'], 1)
        self.assertEqual(stages['cycle.research']['outcomes']['skipped'], 1)

    def test_cycle_lock_and_pid_identity_do_not_fake_running_work(self):
        with lockfile(self.root, '.supervisor.lock'):
            with self.assertRaises(BlockingIOError):
                with lockfile(self.root, '.supervisor.lock'):
                    self.fail('overlapping supervisor')
        cycle_store.begin(self.db, 30)
        row = dict(self.db.execute('SELECT * FROM cycles').fetchone())
        row['process_start'] = 'old process identity'
        with patch('x_curator.process_liveness.start_mark', return_value='new process identity'):
            self.assertEqual(state(row), 'stopped')

    def test_failed_cycle_retains_action_and_persisted_deadline(self):
        with patch('x_curator.supervisor.phases', side_effect=RuntimeError('synthetic interruption')):
            result = run(self.db, self.root, Client([]), 0, 0, 30)
        self.assertEqual(result['state'], 'blocked')
        row = self.db.execute('SELECT * FROM cycles').fetchone()
        self.assertEqual(row['state'], 'failed')
        self.assertEqual(row['deadline'] - row['started'], 30)
        self.assertIn('synthetic interruption', row['result'])
