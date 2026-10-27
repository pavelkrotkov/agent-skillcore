from x_reading_fixtures import ReadingCase


class ReadingWikiTests(ReadingCase):

    def test_segmented_publication_enters_wiki_with_complete_claims_and_original_provenance(self):
        from x_curator.wiki_sources import sources
        from x_curator.wiki_catalog import prepare
        from x_curator.wiki_build import build
        from x_curator.wiki_store import initialize
        identity = self.publish_reading()
        current = sources(self.db, self.root)
        inputs = prepare(current, {}, [identity])
        source = inputs['sources'][identity]
        self.assertTrue(source['packet']['claims'])
        self.assertIn(self.book, source['provenance'])
        self.assertEqual(source['provenance'][self.book]['url'], 'https://example.test/book')
        initialize(self.db)
        manifest = build(self.db, self.root, current, {})
        page = self.root / 'wiki/builds' / manifest['generation'] / 'docs/sources' / (identity + '.md')
        self.assertIn('The author provides synthetic evidence', page.read_text())
