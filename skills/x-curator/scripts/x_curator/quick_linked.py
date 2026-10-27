"""Capture linked text and choose the bounded checker request shape."""
from .stage_timings import timed
from itertools import filterfalse

from . import quick_store, quick_web
from .quick_sources import register, source
from .receipts import digest
from .quick_tool_feedback import budget
from .source_requirements import links
from .quick_failures import MEDIA_REFUSAL
from .youtube_urls import video_id
from .evidence import save_capture


@timed("source.linked_read", scope="selected")
def capture(db, token, selection):
    urls = list(filterfalse(known_video, links(selection['source']['entry'])))
    if not urls:
        return None
    for url in urls:
        usable, _ = read(db, token, url)
        if usable:
            return True
    return None


def known_video(url):
    try:
        return video_id(url)
    except ValueError:
        return None


def read(db, token, url):
    try:
        result = quick_web.read(db, token, source(db, token, url))
    except (ValueError, OSError) as exc:
        error = str(exc)
        if error == MEDIA_REFUSAL:
            return False, None
        save_capture(db, token, dict(kind='unavailable', url=url, text='', quick_scope=True,
                                    limitations=['Linked source unavailable during bounded prefetch: ' + error[:300]]))
        return False, error
    return result['evidence']['kind'] == 'text', None


def request(db, token, check, evidence, search_mode):
    from .quick_final import FORMAT
    common = dict(role='factcheck', policy=quick_store.POLICY, check=check['id'], deadline=check['deadline'],
                  bundle=evidence, bundle_sha=digest(evidence), proposal=None, final_format=FORMAT, timing=budget(check))
    return dict(common, sources=register(db, token, evidence), search_mode=search_mode)
