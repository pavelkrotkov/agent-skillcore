"""A small concept entry point, with the complete catalog one click away."""
from .wiki_text import document, link, text


def catalog(pages):
    return document(['# All notes'] + [link(page['title'], key + '.md')
                     for key, page in sorted(pages.items(), key=lambda item: item[1]['title'].casefold())])


def home(pages, current, mapping, incoming):
    concepts = starts(pages, incoming)
    entries = [link(pages[key]['title'], key + '.md') + ' — ' + text(pages[key]['description']) for key in concepts]
    mapped = sum(bool(keys) for keys in mapping.values())
    return document(['# Explore connected ideas',
        'Likes are starting points. Explore concept notes, follow explained connections, and open supporting likes for provenance.',
        f'{len(current)} accepted sources; {mapped} organized; {len(current) - mapped} awaiting organization.',
        '## Start exploring', '\n'.join('- ' + entry for entry in entries),
        'Open questions identify gaps. Deeper research requires your explicit approval.',
        link('All notes', 'notes.md'), link('All supporting sources', 'sources/index.md')])


def rank(key, page, incoming):
    sources = len({ref['publication'] for ref in page['claims']})
    return not page.get('entry', False), -len(incoming[key]), -sources, page['title'].casefold(), key


def starts(pages, incoming):
    ranked = sorted(pages, key=lambda key: rank(key, pages[key], incoming))
    curated = [key for key in ranked if pages[key].get('entry') and pages[key]['kind'] == 'concept']
    return [key for key in (curated or ranked) if pages[key]['kind'] == 'concept'][:12]
