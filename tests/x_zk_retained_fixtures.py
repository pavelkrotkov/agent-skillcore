from x_fixtures import SCRIPTS
from x_curator.wiki_catalog import prepare
from x_curator.wiki_keys import page_key
from x_curator.wiki_refresh_store import fingerprint
from x_curator.wiki_retained_assignments import VERSION


def inputs_and_pages():
    refs = [dict(publication='source', claim=str(i)) for i in range(2)]
    sources = {'source': {'packet': {'claims': [dict(id=str(i), text='Attributed idea.',
                    kind='opinion', attribution='Synthetic author', limitations=[]) for i in range(2)]}}}
    pages = [dict(kind='concept', title=f'Distinct scope {i}', description='Synthetic idea.',
                      aliases=[], claims=[ref], related=[],
                      synthesis=[dict(text='Attributed idea.', claims=[ref])])
                  for i, ref in enumerate(refs)]
    catalog = {page_key(page): page for page in pages}
    inputs = prepare(sources, catalog, ['source'], list(catalog))
    inputs.update(refresh=fingerprint(inputs), retained_assignments=VERSION)

    return inputs, pages
