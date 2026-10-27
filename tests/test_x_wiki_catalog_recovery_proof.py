from x_wiki_fixtures import WikiCase
from x_trace_fixtures import proof
from x_publication_fixtures import events
from x_curator import wiki_store
from x_curator.receipts import digest, encoded
from x_curator.wiki_keys import page_key
from x_curator.wiki_prompts import request
from x_curator.wiki_catalog_recovery import required_keys


class CatalogRecoveryProofTests(WikiCase):
    def test_unsigned_stale_and_changed_receipts_cannot_select_meanings(self):
        target = page_key(self.mapping['pages'][0])
        inputs = dict(self.inputs, known_keys=[target])
        packet = dict(self.mapping, input_sha=digest(inputs))
        identity = wiki_store.reserve(self.db, inputs)
        valid = proof(request('organize', inputs), packet)
        wiki_store.receipt(self.db, identity, 'proposal', valid)
        wiki_store.fail(self.db, identity, 'existing page meaning was absent')
        self.assertEqual(required_keys(self.db, inputs), {target})
        for invalid in (b'[null]', events(packet), proof(request('organize', inputs), dict(packet, input_sha='stale')),
                        proof(request('organize', dict(inputs, catalog_sha='changed')), packet)):
            self.db.execute('UPDATE wiki_runs SET proposal=? WHERE id=?', (invalid, identity))
            self.assertEqual(required_keys(self.db, inputs), set())
        self.db.execute('UPDATE wiki_runs SET proposal=?,input=? WHERE id=?',
                        (valid, encoded(dict(inputs, catalog_sha='tampered')).decode(), identity))
        self.assertEqual(required_keys(self.db, inputs), set())
