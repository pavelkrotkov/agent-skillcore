from unittest.mock import patch

from x_wiki_fixtures import WikiCase
from x_curator.wiki import run, candidates
from x_curator.wiki_mapping import map_sources
from x_curator.wiki_recovery import grant
from x_curator.wiki_store import reserve, fail


class WikiOperatorRecoveryTests(WikiCase):
    def exhaust(self, count):
        with patch('x_curator.wiki_mapping.runner', side_effect=RuntimeError('synthetic outage')):
            for _ in range(count):
                with self.assertRaises(RuntimeError):
                    map_sources(self.db, self.inputs)

    def test_one_grant_preserves_history_and_reenables_real_mapping(self):
        self.exhaust(3)
        history = self.db.execute('SELECT * FROM wiki_runs ORDER BY id').fetchall()
        self.assertEqual(candidates(self.db, self.sources), [])
        result = grant(self.db, self.publication, 'Qualified repaired catalog')
        self.assertEqual(result['attempt_limit'], 4)
        self.assertEqual(candidates(self.db, self.sources), [self.publication])
        with self.assertRaises(ValueError):
            grant(self.db, self.publication, 'Duplicate grant')
        with patch('x_curator.wiki_mapping.runner', return_value=self.model):
            self.assertEqual(run(self.db, self.root)['mapped_sources'], 1)
        self.assertEqual(self.db.execute('SELECT * FROM wiki_runs WHERE state=\'failed\' ORDER BY id').fetchall(), history)
        self.assertEqual(self.db.execute('SELECT attempts FROM wiki_sources').fetchone()[0], 4)
        with self.assertRaises(ValueError):
            grant(self.db, self.publication, 'Already mapped')

    def test_lifetime_grants_are_bounded_without_resetting_attempts(self):
        self.exhaust(3)
        for _ in range(2):
            grant(self.db, self.publication, 'Qualified repair')
            self.exhaust(1)
        with self.assertRaises(ValueError):
            grant(self.db, self.publication, 'Third grant')
        self.assertEqual(self.db.execute('SELECT attempts FROM wiki_sources').fetchone()[0], 5)
        self.assertEqual(self.db.execute('SELECT count(*) FROM wiki_recovery_grants').fetchone()[0], 2)

    def test_active_mapping_and_withdrawn_publication_reject_grants(self):
        self.exhaust(2)
        identity = reserve(self.db, self.inputs)
        with self.assertRaisesRegex(ValueError, 'active'):
            grant(self.db, self.publication, 'Must wait for active run')
        fail(self.db, identity, 'synthetic failure')
        with self.db:
            self.db.execute("UPDATE publications SET state='invalid'")
        with self.assertRaises(ValueError):
            grant(self.db, self.publication, 'Withdrawn source')
        self.assertEqual(self.db.execute('SELECT count(*) FROM wiki_recovery_grants').fetchone()[0], 0)
