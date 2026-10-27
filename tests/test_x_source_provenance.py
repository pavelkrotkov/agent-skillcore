import unittest
from markdown import markdown

from x_curator.html_text import Links
from x_curator.wiki_source_render import source


class SourceProvenanceTests(unittest.TestCase):
    def test_factual_source_page_links_to_origin_even_without_an_X_citation(self):
        claim = dict(id='c1', text='A documented capability.', kind='fact', attribution='Official project',
                     limitations=[], citations=[dict(capture='primary')])
        packet = dict(title=dict(text='Documented tool'), summary=dict(text=claim['text']),
                      bundle_sha='retained-bundle', claims=[claim], limitations=[])
        item = dict(packet=packet, created=0, source='123456',
                    provenance=dict(primary=dict(url='https://example.test/primary')))
        parser = Links()
        parser.feed(markdown(source('publication',item,{},[]).decode()))
        self.assertIn('https://example.test/primary', parser.urls)
        self.assertIn('https://x.com/i/status/123456', parser.urls)
