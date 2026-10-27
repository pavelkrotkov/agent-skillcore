"""Assess source authority and independence separately from knowledge admission."""
from urllib.parse import urlsplit

from .claim_validation import nonempty
from .quick_citations import validate_source


def support(check, captures):
    sources = check['sources']
    for source in sources:
        validate_source(source, captures)
    credible = [s for s in sources if s['credible']]
    if not any(s['primary'] for s in credible) and independent(credible, captures) < 2:
        raise ValueError('one authoritative primary or two independent credible origins required')



def independent(sources, captures):
    origins = {s['origin'].strip().casefold() for s in sources}
    hosts = {urlsplit(captures[s['capture']]['url']).hostname.rstrip('.').removeprefix('www.') for s in sources}
    bodies = {captures[s['capture']]['body_sha'] for s in sources}
    return min(len(origins), len(hosts), len(bodies))


def validate_check(row, captures):
    nonempty(row['text'])
    if row['status'] not in ('supported', 'disproven', 'inconclusive', 'subjective'):
        raise ValueError('unknown fact-check result')
    if row['status'] in ('supported', 'disproven'):
        support(row, captures)
