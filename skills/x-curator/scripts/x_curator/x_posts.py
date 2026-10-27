"""Only typed, unambiguous post objects qualify as focal X evidence."""
from .entries import availability
from .source_evidence import nodes
from .receipts import digest
from .x_quote_views import quote_view, typed_post


class AmbiguousPost(ValueError):
    pass


def posts(value):
    return filter(None, (typed_post(node) for node in nodes(value)))


def unique_focal(recovered, requested):
    matches = [post for post in recovered if post['rest_id'] == requested]
    if not matches:
        raise ValueError('X detail focal is absent')
    expanded = max(matches, key=lambda post: bool(post.get('quoted_status_result')))
    if len({digest(quote_view(post, expanded)) for post in matches}) != 1:
        raise AmbiguousPost('X detail focal is ambiguous')
    return expanded


def negative(value, requested):
    return any(unavailable(node, requested) for node in nodes(value))


def unavailable(node, requested):
    if node.get('entryId') == 'tweet-' + requested:
        return availability(node, requested) != 'available'
    return node.get('rest_id') == requested and node.get('__typename') in ('TweetUnavailable', 'TweetTombstone')
