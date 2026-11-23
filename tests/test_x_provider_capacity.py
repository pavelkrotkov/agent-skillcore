from unittest.mock import patch

from x_native_search_fixtures import NativeCase
from x_fixtures import Client
from x_curator import execution_failure, provider_health, quick_process
from x_curator.deadlines import DeadlineExceeded
from x_curator.receipts import encoded
from x_curator.worker import work

MESSAGE = 'Reconnecting... 1/5 (Selected model is at capacity. Please try a different model.)'
EVENT = encoded(dict(type='error', message=MESSAGE)) + b'\n'


class ProviderCapacityTests(NativeCase):
    def test_native_capacity_deadline_pauses_following_work(self):
        error = DeadlineExceeded('execution deadline exhausted')
        error.log = EVENT
        with patch('x_curator.quick_process.runner', return_value=lambda _: self.raise_capacity(error)):
            quick_process.research(self.db, self.root, self.client, self.token)
        self.assertIsNotNone(provider_health.blocked(self.db))
        before = self.db.execute('SELECT count(*) FROM attempts').fetchone()[0]
        result = work(self.db, self.root, Client([]), 2)
        self.assertEqual((result['state'], result['attempted']), ('blocked', 0))
        self.assertEqual(self.db.execute('SELECT count(*) FROM attempts').fetchone()[0], before)
        self.assertEqual(self.db.execute('SELECT count(*) FROM publications').fetchone()[0], 0)

    def raise_capacity(self, error):
        raise error

    def test_only_unfinished_native_capacity_deadline_is_a_provider_failure(self):
        deadline = DeadlineExceeded('execution deadline exhausted')
        self.assertIsNotNone(execution_failure.provider_failure(deadline, EVENT))
        for log in (EVENT + encoded(dict(type='turn.completed')),
                    encoded(dict(type='item.completed', item=dict(type='agent_message', text=MESSAGE))),
                    EVENT.replace(b'Selected model is at capacity.', b'Unrelated failure.')):
            with self.subTest(log=log):
                self.assertIsNone(execution_failure.provider_failure(deadline, log))
        self.assertIsNone(execution_failure.provider_failure(ValueError('local defect'), EVENT))
