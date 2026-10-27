"""Controller retrieval uses X session auth only for canonical X post detail calls."""
from .x_urls import focal_id

from . import blobs, x_detail, x_thread, x_derived, dropbox, youtube
from .youtube_urls import video_id
from .evidence import bundle, save_capture
from .readers import extract, needs_extract
from .retrievals import retrieve
from .reuse import captures as reusable_captures


def acquire(db, token, url, fetcher, cached=None):
    if video_id(url):
        return youtube.capture(db, token, url, cached)
    cached = x_derived.find(db, bundle(db, token), url, dropbox.reusable(cached))
    payload = dict(cached) if cached else retrieve(db, token, url, fetcher)
    requested = focal_id(payload)
    if requested and "json" in payload["mime"]:
        body = blobs.read(db, payload["body_sha"])
        payload.update(x_detail.extract(body, requested, x_thread.selected_scope(db, token, body, requested)))
    elif needs_extract(cached):
        payload = extract(db, payload)
    return save_capture(db, token, payload)


def acquire_urls(db, token, urls, fetcher):
    pending = remaining(db, token, urls)
    cache = reusable_captures(db, token)
    root = "https://x.com/i/status/" + bundle(db, token)["source"]
    while pending:
        url = root if root in pending else min(pending, key=lambda value: (value not in cache, -cache.get(value, {}).get('fetched', 0), value))
        acquire(db, token, url, fetcher, cache.get(url))
        pending = remaining(db, token, pending)


def remaining(db, token, urls):
    evidence = bundle(db, token)["captures"].values()
    acquired = {c["url"] for c in evidence if c["kind"] not in ("selection", "unavailable")}
    required = {u for c in evidence for u in c.get("required_urls", [])}
    return (set(urls) | required) - acquired
