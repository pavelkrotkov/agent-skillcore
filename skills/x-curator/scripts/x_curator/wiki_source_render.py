"""Every source revision exposes original evidence and knowledge backlinks."""
from urllib.parse import quote

from .wiki_text import claim_lines, date, document, link, text
from .pdf_links import target, label


def source(identity,item,pages,keys):
    packet = item['packet']
    parts = ['# ' + text(packet['title']['text']), text(packet['summary']['text']),
             'Researched: ' + date(item['created']), 'Publication revision: `' + identity + '`',
             'Evidence bundle: `' + packet['bundle_sha'] + '`', link('X source', 'https://x.com/i/status/' + item['source'])]
    for claim in packet['claims']:
        parts.extend(['## ' + text(claim['id'])] + claim_lines(claim))
        parts.append('Evidence: ' + ', '.join(evidence_link(item['provenance'][c['capture']]['url'], c) for c in claim['citations']))
    parts.extend(['## Limitations', text('; '.join(packet['limitations'])), '## Knowledge pages'])
    parts.extend(link(pages[key]['title'],'../'+key+'.md') for key in keys)
    return document(parts)


def evidence_link(url, citation=None):
    citation = citation or {}
    return link('Source capture' + label(citation), quote(target(url, citation), safe=':/?=&%#@-+_.'))
