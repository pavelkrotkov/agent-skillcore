from unittest.mock import patch

from x_fixtures import Client, CollectionCase, collect, response
from x_curator.intake import poll
from x_curator.intake_store import begin
from x_curator.collect import request_page


class IntakeTests(CollectionCase):
    def test_new_selection_frontier_and_poll_interval_preserve_historical_boundary(self):
        collect(self.db, Client([(200, response(['1']))]), 'likes', delay=0)
        with patch('x_curator.intake.time.sleep'):
            result = poll(self.db, Client([(200, response(['2'], 'next')), (200, response(['1'], 'older'))]), 'likes')
        self.assertEqual((result['state'], result['selected']), ('caught_up', 2))
        self.assertFalse(result['historical_complete'])
        self.assertEqual(poll(self.db, Client([]), 'likes')['id'], result['id'])

    def test_restart_retains_deadline_cursor_and_reserved_request_budget(self):
        client = Client([(200, response(['1'], 'next'))])
        run, _ = begin(self.db, client, 'likes')
        request_page(self.db, client, run)
        receipt = dict(self.db.execute('SELECT * FROM intake_runs').fetchone())
        with self.db:
            self.db.execute('UPDATE intake_runs SET request_limit=1')
        result = poll(self.db, Client([]), 'likes')
        self.assertEqual((result['id'], result['requests'], result['state']), (run['id'], 1, 'blocked'))
        self.assertEqual(self.db.execute('SELECT deadline FROM intake_runs').fetchone()[0], receipt['deadline'])
        self.assertIn('budget exhausted', result['reason'])

    def test_expired_poll_does_not_make_another_request(self):
        run, _ = begin(self.db, Client([]), 'likes')
        with self.db:
            self.db.execute('UPDATE intake_runs SET deadline=0')
        result = poll(self.db, Client([]), 'likes')
        self.assertEqual((result['id'], result['requests'], result['state']), (run['id'], 0, 'blocked'))
        self.assertIn('deadline', result['reason'])
