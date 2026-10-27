from unittest import TestCase
from unittest.mock import patch
from pathlib import Path

from x_fixtures import SCRIPTS
from x_curator import wiki_prompts, native_search, process_group, quick_profile
from x_curator.codex_profile import execution_timeout
from x_curator.wiki_refresh_store import fingerprint


class ZKLimitsTests(TestCase):
    def test_refresh_allowance_identity_uses_the_exact_immutable_source_selection(self):
        selection = {'sources': {'first': {}, 'second': {}}}
        reordered = {'sources': {'second': {}, 'first': {}}}
        self.assertEqual(fingerprint(selection), fingerprint(reordered))
        self.assertNotEqual(fingerprint(selection), fingerprint({'sources': {'first': {}}}))

    def test_only_organizer_searches_and_its_tools_and_time_remain_bounded(self):
        inputs = {'organization': 'zettelkasten/v1'}
        request = wiki_prompts.request('organize', inputs)
        review = wiki_prompts.request('organize_review', inputs)
        self.assertTrue(native_search.enabled(request))
        self.assertFalse(native_search.enabled(review))
        self.assertEqual((execution_timeout(request), execution_timeout(review)), (120, 600))
        with patch('x_curator.blobs.state_root', return_value=Path('/synthetic')):
            for role, names in [('organize', '["context", "validate"]'), ('organize_review', '["validate"]')]:
                args = quick_profile.configure([], None, 'wiki_synthetic', role, native=True)
                self.assertIn('mcp_servers.curator.enabled_tools=' + names, args)

    def test_organization_uses_the_process_group_deadline_path(self):
        request = wiki_prompts.request('organize', {'organization': 'zettelkasten/v1'})
        with patch.object(process_group, 'run', return_value=0) as run, \
                patch.object(process_group, 'until') as deadline, patch.object(process_group.time, 'time', return_value=100):
            self.assertEqual(process_group.execute(['synthetic'], b'', request), 0)
        deadline.assert_called_once_with(220)
        run.assert_called_once()
