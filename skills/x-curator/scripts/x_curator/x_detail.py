"""Recover scoped X context and its obligations from the retained HTTP response."""
from marshal import dumps, loads
from functools import lru_cache

from .source_evidence import strings
from .x_posts import unique_focal, AmbiguousPost
from .x_response_index import indexed
from .source_requirements import tweet_requirements


def validate(body, requested):
    return tuple(loads(authenticated(body, requested)))


@lru_cache(maxsize=8)
def authenticated(body, requested):
    recovered, denied, errors = loads(indexed(body))
    if requested in denied:
        raise AmbiguousPost('X detail focal has an unavailable or malformed result')
    if errors:
        raise ValueError("X detail did not recover the requested source")
    return dumps([unique_focal(recovered, requested), recovered], 2)


def scope(body, requested):
    focal, _ = validate(body, requested)
    legacy = focal.get("legacy", {})
    return [legacy.get("user_id_str"), legacy.get("conversation_id_str")]


def extract(body, requested, selected_scope=()):
    focal, recovered = validate(body, requested)
    required = set(tweet_requirements(focal))
    if selected_scope and all(selected_scope):
        required.update(thread_urls(recovered, *selected_scope))
    required.discard("https://x.com/i/status/" + requested)
    return {"kind": "x_detail", "text": "\n".join(strings(focal)), "required_urls": sorted(required),
            "extraction_policy": "selected-thread-v1", "thread_scope": list(selected_scope),
            "limitations": ["Only the selected author/conversation is expanded into a visible thread. "
                "Foreign surrounding conversations and hidden reply pagination are not exhaustively read."]}


def thread_urls(recovered, author, conversation):
    for post in recovered:
        legacy = post.get("legacy", {})
        if legacy.get("user_id_str") == author and legacy.get("conversation_id_str") == conversation:
            yield "https://x.com/i/status/" + post["rest_id"]
