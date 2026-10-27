import json

from x_wiki_fixtures import WikiCase
from x_curator.html_text import Links
from x_curator.wiki_links import validate
from x_curator.wiki_site import render_site


class WikiNavigationTests(WikiCase):
    def test_search_and_indexes_reach_catalog_without_repeating_it_on_detail_pages(self):
        prefix = 'wiki/builds/synthetic'
        self.write_catalog(self.root / prefix / 'docs', 4)
        site = render_site(self.root, prefix)
        self.assertEqual(validate(site), 11)
        search = json.loads((site / 'search/search_index.json').read_text())
        locations = {row['location'].split('#')[0] for row in search['docs'] if row['text'].strip()}
        expected = {f'{kind}/item-{i}.html' for kind in ('concepts', 'sources') for i in range(4)}
        self.assertTrue(expected <= locations)
        for index, prefix in (('index.html', 'concepts/'), ('sources/index.html', '')):
            self.assertEqual((site / index).read_text().count('href="' + prefix + 'item-'), 4)
        parser = Links()
        parser.feed((site / 'concepts/item-0.html').read_text())
        self.assertIn('../sources/item-0.html', parser.urls)
        self.assertNotIn('../sources/item-1.html', parser.urls)

    def write_catalog(self, docs, count):
        for kind, other in (('concepts', 'sources'), ('sources', 'concepts')):
            (docs / kind).mkdir(parents=True)
            for i in range(count):
                (docs / kind / f'item-{i}.md').write_text(f'# {kind} {i}\n\n[Related](../{other}/item-{i}.md)\n')
        (docs / 'index.md').write_text('# Knowledge\n\n' + '\n'.join(f'- [Concept {i}](concepts/item-{i}.md)' for i in range(count)))
        (docs / 'sources/index.md').write_text('# Sources\n\n' + '\n'.join(f'- [Source {i}](item-{i}.md)' for i in range(count)))
