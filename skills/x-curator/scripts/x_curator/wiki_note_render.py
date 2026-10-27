"""Readable synthesis and source children precede the retained evidence ledger."""
from .wiki_text import link, text, claim_lines, date
from .wiki_keys import reference


def prose(page, name, heading):
    blocks = page.get(name, [])
    return [heading] + [text(block['text']) + '\n\n' + support(block['claims']) for block in blocks] if blocks else []


def support(refs):
    return 'Supported by: ' + ', '.join(link(str(index), '../sources/' + identity + '.md')
        for index, identity in enumerate(sorted({ref['publication'] for ref in refs}), 1))


def source_children(page, current):
    return ['- ' + link(current[identity]['packet']['title']['text'], '../sources/' + identity + '.md')
            for identity in sorted({ref['publication'] for ref in page['claims']})]




def ledger(page, current, claims):
    parts = []
    for ref in sorted(page['claims'], key=reference):
        identity, claim_id = reference(ref)
        parts.extend(claim_lines(claims[(identity, claim_id)]))
        parts.append('Researched ' + date(current[identity]['created']) + ' — ' + link('Source and provenance', '../sources/' + identity + '.md'))
    return parts
