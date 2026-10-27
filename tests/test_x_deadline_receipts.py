from x_native_search_fixtures import NativeCase
import sys
import time
from unittest.mock import patch

from x_curator import executions, process_group, quick_process, quick_store
from x_curator.receipts import digest


class DeadlineReceiptTests(NativeCase):
    def shortened_start(self, db, token, started):
        check = self.original_start(db, token, started)
        with db:
            db.execute('UPDATE quick_checks SET deadline=? WHERE id=?', (time.time() + 0.3, check['id']))
        return dict(db.execute('SELECT * FROM quick_checks WHERE id=?', (check['id'],)).fetchone())

    def timed_runner(self, request):
        root = self.root / 'runs' / self.token
        root.mkdir(parents=True)
        output = root / (digest(request) + '.jsonl')
        script = 'import sys,time; sys.stdout.buffer.write(%r); sys.stdout.flush(); time.sleep(30)' % self.search_log
        with output.open('wb') as stream:
            return process_group.execute([sys.executable, '-c', script], b'', request, output=output, stdout=stream)

    def test_expired_parent_signal_cannot_interrupt_partial_receipt_persistence(self):
        self.original_start = quick_store.start
        original_record = executions.record_log
        def slow_persist(db, identity, log):
            time.sleep(0.02)
            original_record(db, identity, log)
        start = time.monotonic()
        with patch('x_curator.quick_process.runner', return_value=self.timed_runner), \
                patch('x_curator.quick_store.start', self.shortened_start), \
                patch('x_curator.executions.record_log', slow_persist):
            self.assertIsNone(quick_process.research(self.db, self.root, self.client, self.token))
        self.assertLess(time.monotonic() - start, 2)
        execution = self.db.execute('SELECT * FROM executions').fetchone()
        self.assertEqual(execution['log'], self.search_log)
        self.assertIsNone(execution['finished'])
        check = self.db.execute('SELECT * FROM quick_checks').fetchone()
        self.assertEqual((check['searches'], check['outcome']), (4, 'inconclusive'))
