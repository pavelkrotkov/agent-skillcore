"""Bind author identity and cited profile information independently of presentation."""
from .source_evidence import nodes, strings
from .profile_links import quoted_alias

IDENTITY_FIELDS = frozenset(('rest_id', 'id', '__typename'))


def retain_profile_evidence(user, quotes):
    if not isinstance(user.get('rest_id'), str) or not user['rest_id']:
        return
    for name in tuple(user):
        if name not in IDENTITY_FIELDS and not quoted_alias(user[name], quotes):
            user.pop(name)


def nonprofile_strings(value):
    for node in nodes(value):
        if node.get('__typename') == 'User' or ('rest_id' in node and node.keys() <= IDENTITY_FIELDS):
            node.clear()
        else:
            for name in (*IDENTITY_FIELDS, 'id_str', 'quoted_status_permalink'):
                node.pop(name, None)
    return strings(value)
