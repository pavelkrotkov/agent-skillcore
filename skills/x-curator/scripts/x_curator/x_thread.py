"""Freeze thread expansion to the selected post while retaining explicit context links."""
from .evidence import bundle
from .x_urls import focal_id
from . import x_detail


def selected_scope(db, token, body, requested):
    evidence = bundle(db, token)
    for capture in evidence["captures"].values():
        if capture["kind"] == "x_detail" and focal_id(capture) == evidence["source"]:
            return capture["thread_scope"]
    return x_detail.scope(body, requested) if requested == evidence["source"] else []


def reply_urls(recovered, selected, conversation):
    for post in recovered:
        legacy = post.get("legacy", {})
        if legacy.get("in_reply_to_status_id_str") == selected and legacy.get("conversation_id_str") == conversation:
            yield "https://x.com/i/status/" + post["rest_id"]
