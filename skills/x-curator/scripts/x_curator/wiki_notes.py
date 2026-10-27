"""Reviewed ZK prose is supported by claims, never a second fact-check channel."""
from .wiki_keys import reference, claim_index

MODE = 'zettelkasten/v1'


def evidence(inputs):
    claims = {reference(item['reference']): item for page in inputs['catalog'] for item in page['evidence']}
    if inputs.get('catalog_projection') == 2:
        selected = claim_index(inputs['sources'])
        claims.update({ref: selected[ref] for ref in claims if ref[0] in inputs['sources']})
    return claims




def blocks(page, name, refs):
    return [block for block in page.get(name, [])
            if {reference(ref) for ref in block['claims']} <= refs]


def refresh(target, page, allowed):
    if 'entry' in page:
        target['entry'] = page['entry']
    if 'synthesis' not in page:
        return
    target.update(description=page['description'], synthesis=blocks(page, 'synthesis', allowed),
                  questions=blocks(page, 'questions', allowed))


def request(role, inputs, proposal=None):
    value = {'role': role, 'bundle': {'captures': {}, 'wiki_inputs': inputs}, 'proposal': proposal}
    if role == 'organize' and inputs.get('organization') == 'zettelkasten/v1':
        value.update(policy='zk-organization/v1', search_mode='codex-native/three-query-target-v1')
        if 'final_format' in inputs:
            value['final_format'] = inputs['final_format']
    return value



def retired(pages):
    return sorted(old for page in pages.values() for old in page.get('redirects', []))
