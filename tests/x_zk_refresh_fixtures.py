"""Mapped source selections for durable organization-only recovery tests."""
from unittest.mock import patch
from x_wiki_fixtures import WikiCase
from x_wiki_arrival_fixtures import publish_arrival
from x_curator import wiki_inputs, wiki_refresh, wiki_store
from x_curator.wiki_catalog import prepare
from x_curator.wiki_mapping import map_sources
from x_curator.wiki_refresh_recovery import grant


class RefreshRecoveryCase(WikiCase):
    def setUp(self):
        super().setUp()
        arrival = publish_arrival(self.db, self.root)
        self.sources = wiki_inputs.sources(self.db, self.root)
        self.inputs = prepare(self.sources, {}, list(self.sources))
        self.mapping['pages'][0]['claims'].append({'publication': arrival, 'claim': 'c1'})
        with patch('x_curator.wiki_mapping.runner', return_value=self.feedback_response):
            map_sources(self.db, self.inputs)
        self.inputs = prepare(self.sources, wiki_inputs.mappings(self.db, self.sources), list(self.sources))
        self.inputs.update(refresh=wiki_refresh.fingerprint(self.inputs), refresh_reason='Synthetic refresh')

    def exhaust(self):
        for _ in range(3):
            wiki_store.fail(self.db, wiki_store.reserve(self.db, self.inputs), 'Synthetic interrupted organization')

    def exhaust_fourth(self):
        self.exhaust()
        grant(self.db, list(self.sources), 'Synthetic fourth approval')
        wiki_store.fail(self.db, wiki_store.reserve(self.db, self.inputs), 'Synthetic fourth interruption')

    def history(self):
        tables = ('executions', 'attempts', 'captures', 'retrievals', 'wiki_refresh_grants')
        rows = {t: list(self.db.execute('SELECT * FROM '+t+' ORDER BY rowid')) for t in tables}
        rows['source_attempts'] = list(self.db.execute('SELECT publication,attempts FROM wiki_sources ORDER BY publication'))
        return (rows,
                {r['id']: r for r in self.db.execute('SELECT * FROM wiki_runs')})

    def assert_history(self, before):
        tables, mappings = self.history()
        self.assertEqual(tables, before[0])
        self.assertTrue(all(mappings.get(key) == row for key, row in before[1].items()))
