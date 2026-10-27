"""Render dated perspectives and approved reciprocal navigation."""
from .wiki_keys import page_key
from .wiki_note_render import prose, source_children, ledger
from .wiki_text import document, link, text


def topic(key, page, current, pages, claims,incoming):
    parts = ['# ' + text(page['title']), text(page['description'])] + prose(page, 'synthesis', '## The idea')
    parts.extend(['## Connected ideas', '\n'.join(related(key, page, pages, incoming))])
    parts.extend(prose(page, 'questions', '## Open questions'))
    parts.extend(['## Supporting likes', '\n'.join(source_children(page, current)), '## Dated evidence and viewpoints'])
    parts.extend(ledger(page, current, claims))
    parts.append(link('Explore', '../index.md'))
    return document(parts)


def related(key, page, pages,incoming):
    links = set()
    for edge in page['related']:
        target = page_key(edge)
        if target in pages:
            links.add('- ' + link(pages[target]['title'], '../' + target + '.md') + ': ' + text(edge['reason']))
    for target in incoming[key]:
        links.add('- Referenced by ' + link(pages[target]['title'], '../' + target + '.md'))
    return sorted(links)


def incoming(pages):
    result={key:[] for key in pages}
    for key,page in pages.items():
        for target in {page_key(edge) for edge in page['related']} & pages.keys():
            result[target].append(key)
    return result
