from copy import deepcopy
from unittest.mock import patch

from x_wiki_fixtures import WikiCase
from x_wiki_arrival_fixtures import publish_arrival
from x_curator import wiki_inputs
from x_curator.wiki_catalog import prepare
from x_curator.wiki_mapping import map_sources
from x_curator.wiki_keys import page_key


class ZKCase(WikiCase):
    def retained_pair(self):
        arrival = publish_arrival(self.db, self.root)
        self.sources = wiki_inputs.sources(self.db, self.root)
        self.inputs = prepare(self.sources, {}, list(self.sources))
        base = deepcopy(self.mapping['pages'][0])
        self.mapping['pages'] = [self.note(base, title, [{'publication': source, 'claim': 'c1'}])
            for title, source in (('Post-specific loop workflow', self.publication), ('Another loop workflow', arrival))]
        with patch('x_curator.wiki_mapping.runner', return_value=self.feedback_response):
            map_sources(self.db, self.inputs)
        pages = wiki_inputs.mappings(self.db, self.sources)
        refs = [ref for page in pages.values() for ref in page['claims']]
        concept = self.note(base, 'Control loops and verification', refs)
        peer = self.note(base, 'Context management', refs[:1])
        concept.update(entry=True, replaces=[{'kind': p['kind'], 'title': p['title']} for p in pages.values()],
                       related=[dict(kind=peer['kind'], title=peer['title'], reason='Checks depend on the context available to the loop.', claims=refs[:1])],
                       questions=[dict(text='Which checks transfer across contexts?', claims=refs)])
        self.mapping['pages'] = [concept, peer]
        return pages, page_key(concept), page_key(peer)

    def note(self, base, title, refs):
        return dict(base, title=title, claims=refs, synthesis=[dict(
            text='The examples illustrate checks within iterative workflows, without establishing universal reliability.', claims=refs)])
