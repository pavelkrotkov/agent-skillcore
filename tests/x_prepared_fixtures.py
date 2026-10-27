from unittest.mock import patch

from x_publication_fixtures import PublicationCase
from x_curator.leases import fail_owned
from x_curator.publication import publish
from x_curator.publication_files import write_verified
from x_curator.retrievals import request


class PreparedCase(PublicationCase):
    def setUp(self):
        super().setUp()
        proposal, review = self.approved_executions()
        request(self.db, self.token, 'https://example.org/synthetic', lambda _: (200, 'text/plain', b'Synthetic response.', None))
        def interrupted(*args):
            write_verified(*args)
            raise RuntimeError('synthetic interruption after prepared file')
        with patch('x_curator.publication.write_verified', side_effect=interrupted), self.assertRaises(RuntimeError):
            publish(self.db, self.root, self.token, proposal, review)
        fail_owned(self.db, self.token, 'synthetic publication failure', 300)
        self.row = dict(self.db.execute('SELECT * FROM publications').fetchone())
        self.identity = self.row['id']
        self.before = self.ledger()

    def ledger(self):
        attempt = tuple(self.db.execute('SELECT * FROM attempts').fetchone())
        budget = tuple(self.db.execute('SELECT attempts,max_attempts FROM jobs').fetchone())
        requests = [tuple(r) for r in self.db.execute('SELECT * FROM retrievals')]
        return attempt, budget, requests
