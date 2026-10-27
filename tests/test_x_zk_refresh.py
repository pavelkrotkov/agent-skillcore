from unittest.mock import patch
from types import SimpleNamespace

from x_wiki_fixtures import WikiCase
from x_curator import wiki_refresh, wiki_store, wiki_inputs
from x_curator.wiki_catalog import prepare
from x_curator.wiki_mapping import map_sources
from x_curator.quick_schema import initialize


class ZKRefreshTests(WikiCase):
    def test_refresh_preserves_factchecks_and_source_attempts_and_has_its_own_limit(self):
        with patch('x_curator.wiki_mapping.runner', return_value=self.feedback_response):
            map_sources(self.db, self.inputs)
        before = tuple(self.db.execute('SELECT attempts,run FROM wiki_sources').fetchone())
        pages = wiki_inputs.mappings(self.db, self.sources)
        inputs = prepare(self.sources, pages, [self.publication])
        inputs.update(refresh=wiki_refresh.fingerprint(inputs), refresh_reason='Synthetic note refresh')
        initialize(self.db)
        checks = self.db.execute('SELECT count(*) FROM quick_checks').fetchone()[0]
        for _ in range(3):
            identity = wiki_store.reserve(self.db, inputs)
            row = self.db.execute('SELECT * FROM wiki_runs WHERE id=?', (identity,)).fetchone()
            self.assertEqual(row['expires'] - row['started'], 600)
            wiki_store.fail(self.db, identity, 'Synthetic organization failure')
        with self.assertRaisesRegex(ValueError, 'budget exhausted'):
            wiki_store.reserve(self.db, inputs)
        self.assertEqual(tuple(self.db.execute('SELECT attempts,run FROM wiki_sources').fetchone()), before)
        self.assertEqual(self.db.execute('SELECT count(*) FROM quick_checks').fetchone()[0], checks)
        self.assertEqual(inputs['refresh'], wiki_refresh.fingerprint(dict(inputs, feedback={'findings': ['advisory']})))
        changed = dict(inputs, publications_sha='unrelated arrival', catalog_sha='changed context', catalog=[], refresh_reason='different reason', link_support='changed contract')
        self.assertEqual(inputs['refresh'], wiki_refresh.fingerprint(changed))
        with self.assertRaisesRegex(ValueError, 'budget exhausted'):
            wiki_store.reserve(self.db, changed)

    def test_refresh_rejects_unbounded_selection_before_loading_history(self):
        args = SimpleNamespace(publication=[self.publication] * 11)
        with patch('x_curator.wiki.initial') as load:
            with self.assertRaisesRegex(ValueError, 'one to ten'):
                wiki_refresh.command(self.db, args)
        load.assert_not_called()
