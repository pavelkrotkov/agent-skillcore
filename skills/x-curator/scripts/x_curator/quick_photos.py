"""Bounded post photos become native model inputs before a quick check starts."""
from .stage_timings import timed
from . import blobs, public_http, x_detail
from .evidence import bundle, save_capture
from .media_inputs import image_suffix, identities
from .retrievals import retrieve
from .x_urls import focal_id
from .quick_photo_scope import bounded_urls, photo_urls

MAX_BYTES = 8 * 1024 * 1024


def posts(db, evidence):
    for capture in evidence['captures'].values():
        if capture['kind'] == 'selection':
            result = capture['source']['entry']['content']['itemContent']['tweet_results']['result']
            yield result.get('tweet', result)
        elif capture['kind'] == 'x_detail':
            yield x_detail.validate(blobs.read(db, capture['body_sha']), focal_id(capture))[0]


def fetch(url):
    status, headers, body = public_http.exchange(url, max_bytes=MAX_BYTES, allow_prefix=False)
    return status, public_http.header(headers, 'content-type') or '', body, public_http.header(headers, 'location')


@timed("source.photo_acquisition", scope="selected")
def capture(db, token):
    evidence = bundle(db, token)
    selected, omitted = bounded_urls(list(posts(db, evidence)), evidence['source'], 32-len(identities(evidence)))
    limits = [f'{omitted} thread photos were not inspected; selected-post photos take priority within the 32-image quick-check cap.'] if omitted else []
    for url in selected:
        payload = retrieve(db, token, url, fetch)
        if not payload['mime'].lower().startswith('image/'):
            raise ValueError('post photo response is not an image')
        image_suffix(blobs.read(db, payload['body_sha']))
        save_capture(db, token, dict(payload, kind='image', text='', images=[payload['body_sha']], quick_scope=True, limitations=limits))
