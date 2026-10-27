"""One authenticated response supplies thread context and bounded direct answers."""
from .stage_timings import timed
from . import blobs, prepared_video, quick_photos, x_derived, x_detail, x_thread
from .acquire import acquire
from .evidence import bundle, capture_selection, save_capture
from .x_urls import source_fetcher


@timed("source.thread_context", scope="selected")
def capture(db, token, client=None):
    selection = capture_selection(db, token)
    if client is not None:
        thread(db, token, client)
    prepared_video.attach(db, token)
    quick_photos.capture(db, token)
    return selection


def thread(db, token, client):
    source = bundle(db, token)['source']
    root = 'https://x.com/i/status/' + source
    identity = acquire(db, token, root, source_fetcher(client))
    evidence = bundle(db, token)
    detail = evidence['captures'][identity]
    scope = detail['thread_scope']
    if len(scope) != 2 or not all(scope):
        raise ValueError('selected post lacks author/conversation identifiers for bounded thread context')
    _, recovered = x_detail.validate(blobs.read(db, detail['body_sha']), source)
    urls = set(x_detail.thread_urls(recovered, *scope)) - {root}
    urls.update(sorted(set(x_thread.reply_urls(recovered, source, scope[1])) - urls)[:16])
    for url in sorted(urls):
        payload = x_derived.find(db, evidence, url)
        if payload is None:
            raise ValueError('visible thread post has no unambiguous authenticated evidence')
        save_capture(db, token, payload)
