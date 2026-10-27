"""Index immutable response bytes once, regardless of how many focal posts are proven."""
from functools import lru_cache
import json
from marshal import dumps

from . import x_posts


@lru_cache(maxsize=8)
def indexed(body):
    payload = json.loads(body)
    posts, denied = [], set()
    for node in x_posts.nodes(payload):
        if post := x_posts.typed_post(node):
            posts.append(post)
        denied.update(identity for identity in identities(node) if x_posts.unavailable(node, identity))
    return dumps([posts, list(denied), bool(payload.get('errors'))], 2)


def identities(node):
    if isinstance(entry := node.get('entryId'), str) and entry.startswith('tweet-'):
        yield entry[6:]
    if isinstance(identity := node.get('rest_id'), str):
        yield identity
