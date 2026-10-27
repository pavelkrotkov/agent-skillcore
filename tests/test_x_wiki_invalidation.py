import json
from unittest.mock import patch

from x_wiki_fixtures import WikiCase
from x_curator.wiki import run
from x_curator.wiki_current import current
from x_curator.wiki_text import document, text


class WikiInvalidationTests(WikiCase):
    def test_corrupt_pointer_is_withdrawn(self):
        pointer = self.root / 'wiki/CURRENT.json'
        pointer.parent.mkdir(parents=True, exist_ok=True)
        pointer.write_text('{damaged')
        with self.assertRaises(ValueError):
            current(self.db, self.root)
        self.assertIsNone(json.loads(pointer.read_text())['generation'])

    def test_withdrawn_source_retracts_current_generation(self):
        with patch('x_curator.wiki_mapping.runner', return_value=self.model):
            run(self.db, self.root)
        with self.db:
            self.db.execute("UPDATE publications SET state='invalid'")
        with self.assertRaisesRegex(ValueError, 'stale'):
            current(self.db, self.root)
        self.assertIsNone(json.loads((self.root / 'wiki/CURRENT.json').read_text())['generation'])

    def test_damaged_site_cannot_remain_current(self):
        with patch('x_curator.wiki_mapping.runner', return_value=self.model):
            report = run(self.db, self.root)
        path = self.root / 'wiki/builds' / report['generation'] / 'site/index.html'
        path.write_text('damaged')
        with self.assertRaisesRegex(ValueError, 'readback'):
            current(self.db, self.root)
        self.assertIsNone(json.loads((self.root / 'wiki/CURRENT.json').read_text())['generation'])

    def test_model_prose_cannot_create_html_or_navigation(self):
        import markdown
        result = markdown.markdown(document([text('<script>attack()</script> [bad](file:///private)')]).decode())
        self.assertNotIn('<script>', result)
        self.assertNotIn('<a ', result)
