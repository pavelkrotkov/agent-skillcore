from unittest import TestCase

from x_fixtures import SCRIPTS
from x_curator.receipts import digest
from x_curator.wiki_catalog import prepare
from x_curator.wiki_keys import page_key
from x_curator.wiki_notes import evidence
from x_curator.wiki_catalog_topics import score


class CatalogRelevanceTests(TestCase):
    def test_topic_matching_ignores_verbose_metadata_and_keeps_required_meanings(self):
        claim = dict(id='c1', text='Use context management with subagents in Claude Code.',
                     kind='recommendation', limitations=['Nuclear policy evidence was not assessed.'])
        current = {'p': dict(packet=dict(claims=[claim]))}
        ref = dict(publication='p', claim='c1')
        def page(title, **values):
            return dict(kind='concept', title=title, description='Context management Claude Code ' * 100,
                        aliases=[], related=[], claims=[ref], **values)
        related = page('Context management')
        named = page('Coding assistant')
        named['aliases'] = ['Claude Code']
        noise = page('Nuclear policy')
        substring = page('Agent training')
        partial = page('Context management and gambling')
        entry = page('Context management using isolated subagents', entry=True)
        peer = page('Retained peer')
        required = page('Distinct retained topic')
        required['related'] = [dict(kind=peer['kind'], title=peer['title'])]
        pages = {page_key(p): p for p in (related, named, noise, substring, partial, entry, required, peer)}
        inputs = prepare(current, pages, ['p'], [page_key(required)])
        self.assertEqual({p['title'] for p in inputs['catalog']},
                         {related['title'], named['title'], entry['title'], required['title'], peer['title']})
        self.assertEqual(inputs['catalog'][0]['title'], required['title'])
        self.assertEqual(evidence(inputs), {('p', 'c1'): claim})
        self.assertEqual(inputs['known_keys'], sorted(pages))
        self.assertEqual(inputs['catalog_sha'], digest(pages))
        self.assertEqual(inputs['publications_sha'], digest(current))

    def test_version_identifiers_are_required_even_for_broad_entry_points(self):
        current = {'p': dict(packet=dict(claims=[dict(id='c1', text='Use Python 3.')]))}
        pages = {page_key(p): p for p in [dict(kind='concept', title=title,
                 description='Python migration.', aliases=['Python'], related=[],
                 claims=[dict(publication='p', claim='c1')], entry=True)
                 for title in ('Python 2', 'Python 3')]}
        inputs = prepare(current, pages, ['p'], [next(k for k,p in pages.items() if p['title']=='Python 3')])
        self.assertEqual([p['title'] for p in inputs['catalog']], ['Python 3'])

    def test_embedded_cjk_names_match_without_weakening_latin_or_version_boundaries(self):
        for title, text in [('深度学习', '我正在学习深度学习模型。'),
                            ('GPT-5.1模型', '使用GPT-5.1模型进行测试。'),
                            ('(C++)', 'Use (C++) here.'),
                            ('Claude Code', 'Claude Codeを推奨する')]:
            self.assertFalse(score(dict(title=title), text)[0])
        self.assertEqual(score(dict(title='Python 2'), 'Python 3'), (True, 0))
        self.assertEqual(score(dict(title='Context'), 'contextual'), (True, 0))
