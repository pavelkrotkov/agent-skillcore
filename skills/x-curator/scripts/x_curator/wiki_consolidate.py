"""Replay reviewed consolidations while keeping old note URLs reachable."""
from .wiki_keys import page_key


def apply(pages, proposed):
    for page in proposed:
        target = pages.get(page_key(page))
        if target is not None:
            for previous in page.get('replaces', []):
                key = page_key(previous)
                old = pages.pop(key, {})
                target['redirects'] = sorted(set(target.get('redirects', []) + old.get('redirects', []) + [key]))
                target['aliases'] = sorted(set(target['aliases'] + old.get('aliases', [])))
                target['related'].extend(old.get('related', []))


def links(pages):
    redirects = {old: key for key, page in pages.items() for old in page.get('redirects', [])}
    for key, page in pages.items():
        page['related'] = [retarget(edge, pages, redirects) for edge in page['related']
                           if redirects.get(page_key(edge), page_key(edge)) != key]
    return pages


def retarget(edge, pages, redirects):
    target = redirects.get(page_key(edge))
    return dict(edge, kind=pages[target]['kind'], title=pages[target]['title']) if target else edge
