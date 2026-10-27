from x_publication_fixtures import PublicationCase
from x_fixtures import Client
from x_curator.leases import claim, fail_owned
from x_curator.recovery import grant, request_limit


class RecoveryTests(PublicationCase):
    def test_grant_preserves_consumed_attempts_and_is_bounded_across_restarts(self):
        with self.db:
            self.db.execute('UPDATE jobs SET attempts=max_attempts')
        fail_owned(self.db, self.token, 'reader policy requires repair', 0)
        before = self.db.execute('SELECT count(*) FROM attempts').fetchone()[0]
        grant(self.db, Client.account, '1', 'qualified reader fix', 20)
        job = claim(self.db, Client.account)
        self.assertEqual((job['attempts'], job['max_attempts']), (4, 4))
        self.assertEqual(request_limit(self.db, Client.account, '1'), 60)
        self.assertEqual(self.db.execute('SELECT count(*) FROM attempts').fetchone()[0], before + 1)
        fail_owned(self.db, job['token'], 'still unresolved', 0)
        grant(self.db, Client.account, '1', 'second bounded qualification')
        job = claim(self.db, Client.account)
        fail_owned(self.db, job['token'], 'retain unresolved', 0)
        with self.assertRaisesRegex(ValueError, 'two lifetime'):
            grant(self.db, Client.account, '1', 'must not grant forever')
        self.assertEqual(self.db.execute('SELECT count(*) FROM recovery_grants').fetchone()[0], 2)

    def test_active_source_cannot_receive_an_extra_allowance(self):
        with self.assertRaises(ValueError):
            grant(self.db, Client.account, '1', 'cannot interfere with leased worker')
        self.assertEqual(request_limit(self.db, Client.account, '1'), 40)
