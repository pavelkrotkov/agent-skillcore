"""A deliberately narrow grammar fails closed instead of guessing item approval."""
import re


def parse(text, delivery, references):
    text = text.strip().removesuffix('\nadded command code key')
    header, *clauses = text.strip().split(';')
    if header.strip() != 'review ' + delivery or not clauses:
        raise ValueError('clarify using the digest ID and explicit item references')
    result = {}
    for clause in clauses:
        match = re.fullmatch(r'\s*(approve|research|defer|exclude)\s+([^;]+?)\s*', clause)
        if match is None:
            raise ValueError('clarify the requested action')
        action, ids = match.groups()
        action = 'research' if action == 'approve' else action
        for reference in ids.split(','):
            add(result, reference.strip(), action, references)
    return result


def add(result, reference, action, references):
    if reference not in references or reference in result:
        raise ValueError('unknown or repeated item reference; clarify before applying')
    result[reference] = action


def human_text(item):
    content = item['content']
    text, = content
    if text['type'] != 'text':
        raise ValueError('an explicit human text reply is required')
    return text['text']
