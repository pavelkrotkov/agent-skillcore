"""Accepted arrivals append without rereading the retained source/mapping catalog."""
from unittest.mock import patch
from x_wiki_fixtures import WikiCase
from x_wiki_arrival_fixtures import publish_arrival
from x_curator import wiki,wiki_inputs
from x_curator.wiki_checkpoint import restore
from x_curator.receipts import digest
from x_curator.wiki_catalog import prepare
from x_curator.wiki_mapping import map_sources


class WikiDeltaTests(WikiCase):
    def test_arrival_uses_retained_catalog_and_matches_full_projection(self):
        with patch('x_curator.wiki_mapping.runner',return_value=self.model):
            wiki.run(self.db,self.root)
        arrival=publish_arrival(self.db,self.root)
        with patch.object(wiki_inputs,'sources',side_effect=AssertionError('reloaded source history')):
            result=wiki.run(self.db,self.root,0)
        self.assertEqual((result['verified_sources'],result['mapped_sources']),(2,1))
        snapshot,_=restore(self.db,self.root)
        self.assertIn(arrival,snapshot.values[0])
        self.assertEqual(digest(snapshot.values[2]),digest(wiki_inputs.mappings(self.db,snapshot.values[0])))

    def test_retained_packet_restores_claims_missing_from_the_previous_catalog(self):
        arrival=publish_arrival(self.db,self.root)
        current=wiki_inputs.sources(self.db,self.root)
        self.inputs=prepare(current,{},list(current))
        self.mapping['input_sha']=digest(self.inputs)
        self.mapping['pages'][0]['claims'].append({'publication':arrival,'claim':'c1'})
        with patch('x_curator.wiki_mapping.runner',return_value=self.model):
            map_sources(self.db,self.inputs)
        self.db.execute("UPDATE publications SET state='held-fixture' WHERE id=?",(arrival,));self.db.commit()
        wiki.run(self.db,self.root,0)
        self.db.execute("UPDATE publications SET state='published' WHERE id=?",(arrival,));self.db.commit()
        with patch.object(wiki_inputs,'sources',side_effect=AssertionError('reloaded source history')):
            result=wiki.run(self.db,self.root,0)
        self.assertEqual((result['verified_sources'],result['mapped_sources']),(2,2))
        snapshot,_=restore(self.db,self.root)
        self.assertEqual(digest(snapshot.values[2]),digest(wiki_inputs.mappings(self.db,snapshot.values[0])))
