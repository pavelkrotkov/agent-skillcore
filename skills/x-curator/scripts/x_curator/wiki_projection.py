"""Project verified mapping packets onto the currently accepted source claims."""
from .wiki_keys import claim_index,page_key,reference
from . import wiki_consolidate, wiki_notes


def assemble(current,packets):
    claims,pages=claim_index(current),{}
    for packet in packets.values():
        for page in packet['pages']:
            refs=[ref for ref in page['claims'] if reference(ref) in claims]
            if refs:
                merge(pages,page,refs)
        wiki_consolidate.apply(pages, packet['pages'])
    return wiki_consolidate.links(pages)


def merge(pages, page, refs):
    key = page_key(page)
    target = pages.setdefault(key, dict(page, claims=[], related=[], aliases=[], redirects=[], synthesis=[], questions=[]))
    target['aliases'] = sorted(set(target['aliases'] + [page['title']]))
    target['claims'] = list({reference(r): r for r in target['claims'] + refs}.values())
    allowed = {reference(r) for r in refs}
    wiki_notes.refresh(target, page, allowed)
    target['related'].extend(edge for edge in page['related'] if {reference(r) for r in edge['claims']} <= allowed)
