from unittest.mock import Mock, patch

from x_publication_fixtures import PublicationCase
from x_curator.acquire import acquire
from x_curator.deadlines import DeadlineExceeded
from x_curator.publication import publish
from x_curator.publication_audit import audit
from x_curator.retrieval_store import initialize


class DeadlineIntegrityTests(PublicationCase):
    def test_cache_and_derivation_deadlines_do_not_fall_through_to_http(self):
        initialize(self.db)
        for target in ('usable', 'derive'):
            with self.subTest(target=target):
                fetch = Mock()
                cached = {'kind': 'x_detail', 'url': 'https://x.com/i/status/2', 'final_url': 'https://x.com/i/status/2'} if target == 'usable' else None
                with patch('x_curator.x_derived.' + target, side_effect=DeadlineExceeded('expired')):
                    with self.assertRaises(DeadlineExceeded):
                        acquire(self.db, self.token, 'https://x.com/i/status/2', fetch, cached)
                fetch.assert_not_called()
        self.assertEqual(self.db.execute('SELECT count(*) FROM retrievals').fetchone()[0], 0)

    def test_audit_deadline_does_not_withdraw_authentic_publication(self):
        proposal, review = self.approved_executions()
        publication = publish(self.db, self.root, self.token, proposal, review)
        with patch('x_curator.publication_audit.verify_publication', side_effect=DeadlineExceeded('expired')):
            with self.assertRaises(DeadlineExceeded):
                audit(self.db, self.root)
        row = self.db.execute('SELECT state FROM publications WHERE id=?', (publication,)).fetchone()
        self.assertEqual(row['state'], 'published')
