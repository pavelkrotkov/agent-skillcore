import json
from copy import deepcopy

from x_wiki_saved_draft_fixtures import SavedDraftProofCase, reference_log, broken_log
from x_trace_fixtures import proof
from x_curator import wiki_draft, wiki_final, wiki_saved_draft
from x_curator.receipts import digest, encoded
from x_curator.wiki_notes import request
from x_curator.wiki_prompt_payload import payload
from x_curator.wiki_prompts import prompt
from x_curator.wiki_mapping_receipts import verified
from x_curator.codex_profile import execution_timeout


class SavedDraftProofTests(SavedDraftProofCase):
    def test_exact_pages_links_and_block_citations_survive_short_native_reference(self):
        log = reference_log(self.request, self.proposal, self.args)
        self.assertEqual(wiki_final.output(log, self.inputs), self.proposal)
        self.assertLess(len(encoded(self.args)), 200)
        self.assertEqual(execution_timeout(self.request), 120)
        shown = payload(self.request)
        alias = next(iter(shown['bundle']['wiki_inputs']['sources']))
        self.assertEqual(shown['bundle']['wiki_inputs']['saved_draft']['pages'][0]['claims'][0]['publication'], alias)
        self.assertEqual(shown['bundle']['wiki_inputs']['saved_draft_sha'], self.args['saved_draft_sha'])
        self.assertEqual(wiki_draft.tools()[0]['inputSchema']['required'], ['proposal'])
        self.assertIn('saved_draft_sha', wiki_draft.tools(self.inputs)[0]['inputSchema']['properties'])
        self.assertIn(wiki_saved_draft.INSTRUCTIONS, prompt(self.request))
        self.assertNotIn(wiki_saved_draft.INSTRUCTIONS, prompt(request('organize_review', self.inputs, self.proposal)))

    def test_stale_foreign_mixed_and_tampered_references_fail(self):
        cases = [dict(self.args, input_sha='0'*64), dict(self.args, saved_draft_sha='0'*64),
                 dict(self.args, proposal=self.proposal)]
        for arguments in cases:
            with self.subTest(arguments=arguments), self.assertRaises(ValueError):
                wiki_final.output(reference_log(self.request, self.proposal, arguments), self.inputs)
        changed = deepcopy(self.inputs)
        changed['saved_draft']['pages'][0]['related'] = []
        with self.assertRaises(ValueError):
            wiki_saved_draft.proposal(self.args, changed)
        no_opt_in = dict(self.inputs)
        no_opt_in.pop('saved_draft')
        with self.assertRaises(ValueError):
            wiki_saved_draft.proposal(self.args, no_opt_in)

    def test_reference_needs_successful_same_execution_validation_and_native_completion(self):
        for mode in ('incomplete', 'missing', 'foreign', 'failed'):
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                wiki_final.output(broken_log(self.request, self.proposal, self.args, mode), self.inputs)

    def test_saved_reference_still_requires_authentic_separate_approval(self):
        author = reference_log(self.request, self.proposal, self.args)
        verdict = dict(verdict='approve', input_sha=digest(self.inputs), proposal_sha=digest(self.proposal), findings=[])
        row = dict(input=json.dumps(self.inputs), input_sha=digest(self.inputs), proposal=author,
                   review=proof(request('organize_review', self.inputs, self.proposal), verdict))
        self.assertEqual(verified(row), (self.inputs, self.proposal))
        verdict.update(verdict='reject', findings=['Synthetic unsupported synthesis.'])
        row['review'] = proof(request('organize_review', self.inputs, self.proposal), verdict)
        with self.assertRaisesRegex(ValueError, 'independent approval'):
            verified(row)
        from x_curator.model_events import result
        row['review'] = proof(request('organize_review', self.inputs, self.proposal), verdict, session=result(author)[0])
        with self.assertRaisesRegex(ValueError, 'separate session'):
            verified(row)
