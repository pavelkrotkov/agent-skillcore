"""Bind selected claim assignments from verified notes outside editable context."""
from .wiki_keys import page_key


def omitted(pages,catalog,selected):
    visible = {page_key(page) for page in catalog}
    result = []
    for key,page in pages.items():
        evidence = [dict(reference=ref) for ref in page['claims'] if ref['publication'] in selected]
        if evidence and key not in visible:
            result.append(dict(kind=page['kind'],title=page['title'],complete=True,evidence=evidence))
    return result
