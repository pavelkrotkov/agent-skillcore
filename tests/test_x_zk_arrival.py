from types import SimpleNamespace
from unittest.mock import patch

from x_zk_fixtures import ZKCase
from x_curator import wiki_refresh, wiki, wiki_inputs
from x_curator.wiki_catalog import prepare
from x_curator.wiki_mapping import map_sources
from x_wiki_arrival_fixtures import publish_arrival


class ZKArrivalTests(ZKCase):
    def test_new_source_reuses_the_consolidated_note(self):
        previous, concept, peer = self.retained_pair()
        args = SimpleNamespace(state=self.root, publication=list(self.sources), page=list(previous), reason='Synthetic slice')
        with patch('x_curator.wiki_mapping.runner', return_value=self.feedback_response):
            wiki_refresh.command(self.db, args)
        arrival = publish_arrival(self.db, self.root, '3')
        current = wiki_inputs.sources(self.db, self.root)
        pages = wiki_inputs.mappings(self.db, current)
        self.inputs = prepare(current, pages, [arrival], [concept])
        updated = self.note(pages[concept], pages[concept]['title'], pages[concept]['claims'] + [{'publication': arrival, 'claim': 'c1'}])
        self.mapping['pages'] = [dict(updated, replaces=[])]
        with patch('x_curator.wiki_mapping.runner', return_value=self.feedback_response):
            map_sources(self.db, self.inputs)
        self.assertEqual(wiki.run(self.db, self.root, 0)['mapped_sources'], 3)
        self.assertEqual(set(wiki_inputs.mappings(self.db, current)), {concept, peer})
