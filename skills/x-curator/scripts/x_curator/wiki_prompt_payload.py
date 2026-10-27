"""Bind full controller inputs while showing only organization context to models."""
from .receipts import digest
from .wiki_references import aliases, replace


def payload(request):
    inputs = request['bundle']['wiki_inputs']
    value = dict(request, input_sha=digest(inputs), proposal_sha=digest(request['proposal']))
    if inputs.get('catalog_projection') == 2:
        visible = {key: item for key, item in inputs.items()
                   if key not in ('known_keys', 'retired_keys', 'catalog_sha', 'publications_sha')}
        value['bundle'] = dict(request['bundle'], wiki_inputs=visible)
    if names := aliases(inputs):
        visible = replace(value['bundle']['wiki_inputs'], names)
        visible['sources'] = {names[key]: item for key, item in visible['sources'].items()}
        value = dict(value, bundle=dict(value['bundle'], wiki_inputs=visible),
                     proposal=replace(value['proposal'], names))
    return value
