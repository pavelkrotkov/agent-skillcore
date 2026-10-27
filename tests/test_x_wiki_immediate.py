import json
from unittest.mock import patch

from x_wiki_fixtures import WikiCase
from x_fixtures import Client, collect, envelope
from x_wiki_arrival_fixtures import publish_arrival
from x_curator.wiki import run
from x_curator.wiki_current import current


class WikiImmediateTests(WikiCase):
    def test_publication_is_searchable_without_organizer(self):
        with patch('x_curator.wiki_mapping.runner', return_value=self.model):
            run(self.db, self.root)
        arrival = publish_arrival(self.db, self.root)
        with patch('x_curator.wiki.organize') as organizer:
            report = run(self.db, self.root, 0)
        organizer.assert_not_called()
        self.assertEqual((report['mapped_sources'], report['unmapped_sources']), (1, 1))
        self.assertGreaterEqual(report['verdict_to_index_seconds'], 0)
        manifest = current(self.db, self.root)
        self.assertEqual(set(manifest['sources']), {self.publication, arrival})
        folder = self.root / 'wiki/builds' / manifest['generation'] / 'site/sources'
        self.assertIn('New opinion', (folder / 'index.html').read_text())
        page = (folder / (arrival + '.html')).read_text()
        self.assertIn('New synthetic opinion.', page)
        self.assertIn('Source capture', page)

    def test_metadata_refresh_remains_indexable_without_rewriting_receipts(self):
        originals = {name: [tuple(row) for row in self.db.execute('SELECT * FROM ' + name)]
                     for name in ('captures', 'executions', 'publications')}
        entry = json.loads(self.db.execute('SELECT entry FROM selections LIMIT 1').fetchone()[0])
        post = entry['content']['itemContent']['tweet_results']['result']
        post['legacy']['source'] = 'X for Android'
        profile = post['core']['user_results']['result']
        profile['legacy']['profile_banner_url'] = 'https://example.org/banner'
        profile['legacy']['description'] = 'Uncited refreshed biography'
        profile['profile_bio'] = {'description': 'Uncited refreshed biography'}
        collect(self.db, Client([(200, envelope([{'type': 'TimelineAddEntries', 'entries': [entry]}]))]),
                'likes', new=True, delay=0)
        report = run(self.db, self.root, 0)
        self.assertEqual((report['verified_sources'], set(current(self.db, self.root)['sources'])),
                         (1, {self.publication}))
        self.assertEqual({name: [tuple(row) for row in self.db.execute('SELECT * FROM ' + name)]
                          for name in originals}, originals)
