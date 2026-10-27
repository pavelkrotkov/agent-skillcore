"""Named topics in authentic rejection feedback recover context, not approval."""
import re

from .wiki_mapping_feedback import previous_rejection


def review_keys(db, inputs, pages):
    feedback = previous_rejection(db, inputs)
    if not feedback:
        return set()
    titles = set(re.findall(r'["“]([^"”]+)["”]', '\n'.join(feedback['findings'])))
    titles |= {title.removesuffix('.') for title in titles}
    return {key for key, page in pages.items() if page['title'] in titles or key in titles}
