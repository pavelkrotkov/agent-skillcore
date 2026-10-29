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


    def old_attempt(self):
        with self.db:
            self.db.execute('''INSERT INTO attempts SELECT 'old-attempt',account,id,
                0,1,2,'failed','synthetic superseded attempt' FROM attempts WHERE token=?''', (self.token,))
            self.db.execute('''INSERT INTO executions SELECT id||'-old','old-attempt',role,
                model,input,input_sha,started,finished,session,output,output_sha,log,log_sha
                FROM executions WHERE token=?''', (self.token,))
