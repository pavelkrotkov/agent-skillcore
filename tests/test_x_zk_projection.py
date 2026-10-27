from copy import deepcopy

from x_wiki_fixtures import WikiCase
from x_curator.wiki_projection import assemble
from x_curator.wiki_keys import page_key
from x_curator.wiki_render import render
from x_curator.wiki_catalog import catalog_page
from x_curator.wiki_keys import claim_index


class ZKProjectionTests(WikiCase):
    def test_model_redirect_paths_are_ignored_and_refresh_preserves_reviewed_connections(self):
        old = deepcopy(self.mapping['pages'][0])
        peer = dict(old, title='Peer concept')
        old.update(redirects=['../../private'], related=[dict(kind=peer['kind'], title=peer['title'],
            reason='Old connection', claims=old['claims'])])
        refreshed = dict(old, related=[])
        packets = {'first': {'pages': [old, peer]}, 'next': {'pages': [refreshed]}}
        pages = assemble(self.sources, packets)
        self.assertEqual(pages[page_key(old)]['related'], old['related'])
        context = catalog_page(pages[page_key(old)], claim_index(self.sources))
        self.assertEqual(context['related'], old['related'])
        self.assertEqual(pages[page_key(old)]['redirects'], [])
        self.assertNotIn('../../private.md', render(self.sources, pages))

    def test_consolidation_retargets_incoming_connections_and_preserves_old_urls(self):
        old = deepcopy(self.mapping['pages'][0])
        peer = dict(old, title='Peer concept', related=[dict(kind=old['kind'], title=old['title'],
            reason='Explicit shared mechanism', claims=old['claims'])])
        middle = dict(old, title='Unified idea', replaces=[old])
        final = dict(old, title='Canonical concept', replaces=[middle])
        pages = assemble(self.sources, {'old': {'pages': [old, peer]},
            'middle': {'pages': [middle]}, 'final': {'pages': [final]}})
        canonical = pages[page_key(final)]
        self.assertEqual(set(canonical['redirects']), {page_key(old), page_key(middle)})
        self.assertEqual(page_key(pages[page_key(peer)]['related'][0]), page_key(final))
