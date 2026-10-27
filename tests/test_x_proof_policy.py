"""Renderer changes do not invalidate independently verified source approvals."""
from unittest import TestCase
from unittest.mock import patch
from types import SimpleNamespace
from x_curator.wiki_index_result import command
from x_curator.proof_mode import FULL
from x_curator.proof_policy import dependencies


class ProofPolicyTests(TestCase):
    def test_source_scope_contains_native_and_media_verifiers_but_not_rendering(self):
        paths,_=dependencies('publication')
        names={p.stem for p in paths}
        self.assertTrue({'model_trace','source_currentness','prepared_video','quick_proof','read_set'}<=names)
        self.assertTrue({'wiki_build','wiki_site','wiki_render','cli'}.isdisjoint(names))

    def test_mapping_scope_keeps_its_approval_and_packet_contract(self):
        paths,_=dependencies('mapping')
        self.assertTrue({'wiki_mapping_receipts','wiki_contract','model_trace'}<={p.stem for p in paths})

    def test_explicit_maintenance_never_invokes_an_organizer_batch(self):
        args=SimpleNamespace(audit=True,max_sources=10,state='unused')
        with patch('x_curator.wiki.run',return_value={}) as run:
            command(None,args)
        run.assert_called_once_with(None,'unused',0)
        self.assertFalse(FULL.get())
