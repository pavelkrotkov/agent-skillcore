"""Synthetic completed publication and mapping for irreversible proof-migration tests."""
from unittest.mock import patch
from x_wiki_fixtures import WikiCase
from x_curator.publication_audit import verify_publication
from x_curator.wiki_mapping import map_sources


class CompactCase(WikiCase):
    def setUp(self):
        super().setUp()
        with patch('x_curator.wiki_mapping.runner', return_value=self.model):
            map_sources(self.db, self.inputs)
        self.db.commit()


    def verified(self):
        row = self.db.execute('SELECT * FROM publications WHERE id=?', (self.publication,)).fetchone()
        return verify_publication(self.db, self.root, row)
