"""Extract readable evidence while retaining its original acquisition bytes."""
from .stage_timings import timed
import json

from . import blobs, dropbox, youtube_redirects
from .html_evidence import read as read_html
from .source_evidence import strings


def needs_extract(cached):
    if not cached or youtube_redirects.is_alias(cached):
        return True
    pdf = cached.get('pdf_download') or cached['mime'].split(';')[0].lower() == 'application/pdf'
    return pdf and cached.get('pdf', {}).get('version') != 1


@timed('source.media_extract', scope='selected')
def extract(db, payload):
    body = blobs.read(db, payload["body_sha"])
    # Page HTML cannot satisfy a video's coverage obligation, including on cached redirects.
    if youtube_redirects.is_alias(payload):
        return youtube_redirects.metadata(payload)
    mime = dropbox.reader_mime(payload, body)
    if mime.startswith("image/"):
        return dict(payload, kind="image", text="", images=[payload["body_sha"]])
    if mime.startswith("video/"):
        from .video_evidence import extract_video
        return extract_video(db, payload)
    if mime in ('text/html', 'application/xhtml+xml'):
        return dict(payload, **read_html(body, payload['url']))
    if mime == 'application/pdf':
        from .pdf_reader import extract as extract_pdf
        return extract_pdf(db, payload)
    text = read_text(body, mime)
    if len(text.strip()) < 20:
        raise ValueError("source content unavailable or too sparse; recover original source")
    return dict(payload, kind="text", text=text)


def read_text(body, mime):
    if "json" in mime:
        return "\n".join(strings(json.loads(body)))
    if mime.startswith("text/"):
        return body.decode("utf-8", errors="replace")
    raise ValueError("source format requires a reader")
