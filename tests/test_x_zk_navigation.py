from x_wiki_fixtures import WikiCase
from x_curator.wiki_render import render
from x_curator.wiki_keys import page_key


class ZKNavigationTests(WikiCase):
    def test_entry_points_are_small_and_the_complete_catalog_remains_reachable(self):
        base = self.mapping['pages'][0]
        pages = {page_key(page): page for page in (dict(base, title=f'Idea {i}') for i in range(50))}
        files = render(self.sources, pages)
        self.assertEqual(files['index.md'].count(b'](concepts/'), 12)
        self.assertEqual(files['notes.md'].count(b'](concepts/'), 50)
        self.assertIn(b'](notes.md)', files['index.md'])
        selected = list(pages)[:2]
        for key in selected:
            pages[key]['entry'] = True
        entity = dict(base, kind='entity', title='Example entity', entry=True)
        pages[page_key(entity)] = entity
        files = render(self.sources, pages)
        self.assertEqual(files['index.md'].count(b'](concepts/'), 2)
        self.assertIn(b'## Supporting likes', files[selected[0] + '.md'])
