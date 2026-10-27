"""The full runner profile selects HTTPS without changing authentication or tools."""
from pathlib import Path
import unittest
from unittest.mock import patch

from x_curator.codex_runner import arguments


class SubscriptionTransportTests(unittest.TestCase):
    def test_search_and_review_use_only_the_pinned_chatgpt_https_route(self):
        for role, search in (('discover', 'live'), ('review', 'disabled')):
            request = dict(role=role, bundle={'captures': {}}, proposal={})
            with self.subTest(role=role), patch('x_curator.codex_runner.attachments', return_value=[]):
                args = arguments(None, Path('/synthetic-run'), 'codex', request)
                settings = dict(args[i + 1].split('=', 1) for i, arg in enumerate(args) if arg == '-c')
                self.assertEqual(settings['model_provider'], '"openai_https"')
                self.assertEqual(settings['model_providers.openai_https.name'], '"OpenAI"')
                self.assertEqual(settings['forced_login_method'], '"chatgpt"')
                self.assertEqual(settings['model_providers.openai_https.base_url'], '"https://chatgpt.com/backend-api/codex"')
                self.assertEqual(settings['model_providers.openai_https.requires_openai_auth'], 'true')
                self.assertEqual(settings['model_providers.openai_https.supports_websockets'], 'false')
                self.assertEqual(settings['web_search'], '"' + search + '"')
                self.assertEqual(settings['model_reasoning_effort'], '"high"')
                self.assertEqual(args[args.index('--model') + 1], 'gpt-5.6-sol')
                self.assertFalse(any(key.endswith(('env_key', 'bearer_token')) for key in settings))
