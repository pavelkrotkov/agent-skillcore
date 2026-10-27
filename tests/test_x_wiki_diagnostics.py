import subprocess
from unittest.mock import patch

from x_wiki_fixtures import WikiCase
from x_curator.wiki_site import render_site


class WikiDiagnosticTests(WikiCase):
    def test_failed_compiler_retains_diagnostic_without_activating(self):
        messages = [b'synthetic missing anchor', b'synthetic second failure']
        for message in messages:
            error = subprocess.CalledProcessError(1, ['mkdocs'], stderr=message)
            with patch('x_curator.wiki_site.subprocess.run', side_effect=error):
                with self.assertRaises(subprocess.CalledProcessError):
                    render_site(self.root, 'wiki/builds/synthetic')
        logs = (self.root / 'wiki/builds/synthetic/diagnostics').glob('*.txt')
        self.assertEqual({path.read_bytes() for path in logs}, set(messages))
        self.assertFalse((self.root / 'wiki/CURRENT.json').exists())
