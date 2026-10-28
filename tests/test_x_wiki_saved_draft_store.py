import json
import time

from x_wiki_saved_draft_fixtures import SavedDraftStoreCase
from x_curator import wiki_draft, wiki_mcp, wiki_store
from x_curator.receipts import digest
from x_curator.wiki_saved_draft_file import attach


class SavedDraftStoreTests(SavedDraftStoreCase):
    def test_private_file_and_native_mcp_reference_validate_without_store_mutation(self):
        before = '\n'.join(self.db.iterdump())
        attach(self.inputs, self.save(), self.root)
        self.assertEqual('\n'.join(self.db.iterdump()), before)
        identity = wiki_store.reserve(self.db, self.inputs)
        args = dict(input_sha=digest(self.inputs), saved_draft_sha=self.inputs['saved_draft_sha'])
        before = '\n'.join(self.db.iterdump())
        reply = wiki_mcp.respond(self.db, identity, dict(jsonrpc='2.0', id=1, method='tools/call',
                                  params=dict(name='validate', arguments=args)))
        self.assertFalse(reply['isError'])
        self.assertTrue(json.loads(reply['content'][0]['text'])['valid'])
        self.assertEqual('\n'.join(self.db.iterdump()), before)
        row = self.db.execute('SELECT * FROM wiki_runs WHERE id=?', (identity,)).fetchone()
        self.assertEqual((row['state'], row['expires']-row['started']), ('running',600))
        self.assertEqual(self.db.execute('SELECT attempts FROM wiki_sources').fetchone()[0], 1)
        self.assertIsNone(row['proposal'])
        self.assertIsNone(row['review'])

    def test_expiry_cannot_validate_or_renew_the_reserved_attempt(self):
        attach(self.inputs, self.save(), self.root)
        identity = wiki_store.reserve(self.db, self.inputs)
        args = dict(input_sha=digest(self.inputs), saved_draft_sha=self.inputs['saved_draft_sha'])
        with self.db:
            self.db.execute('UPDATE wiki_runs SET expires=? WHERE id=?', (time.time()-1,identity))
        before = '\n'.join(self.db.iterdump())
        self.assertTrue(wiki_draft.call(self.db,identity,'validate',args)['isError'])
        self.assertEqual('\n'.join(self.db.iterdump()), before)

