from copy import deepcopy
import json
import time

from x_wiki_draft_fixtures import WikiDraftCase
from x_curator import wiki_context, wiki_draft, wiki_mcp, wiki_store
from x_curator.wiki_notes import request
from x_curator.wiki_prompt_payload import payload


class WikiContextTests(WikiDraftCase):
    def test_exact_redacted_context_can_correct_feedback_without_mutating_state(self):
        inputs = dict(self.inputs, catalog_projection=2, known_keys=['private'], retired_keys=['private'],
                      catalog_sha='private', publications_sha='private',
                      feedback={'proposal': dict(self.mapping, input_sha='old'), 'findings': ['Correct title.']})
        identity = wiki_store.reserve(self.db, inputs)
        before = '\n'.join(self.db.iterdump())
        response = wiki_mcp.respond(self.db, identity, {'method': 'tools/call',
                                  'params': {'name': 'context', 'arguments': {}}})
        value = response['structuredContent']
        self.assertFalse(response['isError'])
        self.assertEqual(value, payload(request('organize', inputs)))
        self.assertEqual(json.loads(response['content'][0]['text']), value)
        self.assertTrue(set(('known_keys', 'retired_keys', 'catalog_sha', 'publications_sha')).isdisjoint(
            value['bundle']['wiki_inputs']))
        proposal = deepcopy(value['bundle']['wiki_inputs']['feedback']['proposal'])
        self.assertTrue(wiki_draft.call(self.db, identity, 'validate', {'proposal': proposal})['isError'])
        proposal['input_sha'] = value['input_sha']
        self.assertFalse(wiki_draft.call(self.db, identity, 'validate', {'proposal': proposal})['isError'])
        self.assertEqual('\n'.join(self.db.iterdump()), before)

    def test_arguments_missing_superseded_expired_and_changed_inputs_fail_closed(self):
        identity = wiki_store.reserve(self.db, self.inputs)
        for args in ({'id': 'another-run'}, {'path': '/anywhere'}, None, []):
            self.assertTrue(wiki_context.call(self.db, identity, args)['isError'])
        self.assertTrue(wiki_context.call(self.db, 'missing', {})['isError'])
        changes = [('state', 'accepted'), ('expires', time.time() - 1),
                   ('input', json.dumps(dict(self.inputs, changed=True)))]
        for column, value in changes:
            with self.subTest(column=column):
                original = self.db.execute('SELECT ' + column + ' FROM wiki_runs WHERE id=?', (identity,)).fetchone()[0]
                with self.db:
                    self.db.execute('UPDATE wiki_runs SET ' + column + '=? WHERE id=?', (value, identity))
                before = '\n'.join(self.db.iterdump())
                self.assertTrue(wiki_context.call(self.db, identity, {})['isError'])
                self.assertEqual('\n'.join(self.db.iterdump()), before)
                with self.db:
                    self.db.execute('UPDATE wiki_runs SET ' + column + '=? WHERE id=?', (original, identity))
