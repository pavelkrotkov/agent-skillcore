"""Concept pages combine dated approved claims without inventing consensus."""
from .receipts import encoded
from .wiki_keys import claim_index
from .wiki_text import document, link
from .wiki_topic_render import topic,incoming
from .wiki_source_render import source
from . import wiki_navigation


def render(current, pages):
    claims = claim_index(current)
    mapping = source_map(current,pages)
    backlinks = incoming(pages)
    files = {key + '.md': topic(key, page, current, pages, claims,backlinks) for key, page in pages.items()}
    files.update({'sources/' + identity + '.md': source(identity,item,pages,mapping[identity]) for identity, item in current.items()})
    files['index.md'] = wiki_navigation.home(pages, current, mapping, backlinks)
    files['notes.md'] = wiki_navigation.catalog(pages)
    files.update({old + '.md': document(['# Note consolidated', link(page['title'], '../' + key + '.md')])
                  for key, page in pages.items() for old in page.get('redirects', [])})
    files['sources/index.md'] = document(['# Sources'] + [link(item['packet']['title']['text'], identity + '.md')
                                                       for identity, item in sorted(current.items())])
    files['source-map.json'] = encoded(mapping)
    return files




def source_map(current, pages):
    result = {identity: [] for identity in current}
    for key, page in sorted(pages.items()):
        for identity in {ref['publication'] for ref in page['claims']}:
            result[identity].append(key)
    return result
