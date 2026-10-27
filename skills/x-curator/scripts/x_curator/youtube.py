"""Public single-video acquisition joins the normal video reading pipeline."""
from .stage_timings import timed
import time

from . import blobs, youtube_media, youtube_ranges, youtube_resolver, youtube_merge
from .deadlines import until
from .receipts import encoded
from .youtube_urls import video_id
from .youtube_player import selection
from .video_evidence import extract_video


@timed('source.youtube_media', scope='selected', token_arg=True)
def acquire(db, token, url):
    with until(time.time() + 300):
        result, receipts = youtube_resolver.resolve(db, token, url)
        job = db.execute('SELECT account,id FROM attempts WHERE token=?', (token,)).fetchone()
        selected = selection(db, result, receipts, job, url)
        youtube_media.budget(db, token, selected)
        streams = [youtube_ranges.acquire(db, token, value) for value in selected]
        merged = youtube_merge.merge(db, streams, result['duration'])
        manifest = dict(version=1, resolver=youtube_resolver.VERSION, url=url, video_id=video_id(url),
                        result_sha=blobs.put(db, encoded(result)), receipts=receipts, streams=streams, merge=merged)
        manifest_sha = blobs.put(db, encoded(manifest))
        db.execute('''CREATE TABLE IF NOT EXISTS youtube_acquisitions (
            sha TEXT PRIMARY KEY, token TEXT NOT NULL REFERENCES attempts(token))''')
        with db:
            db.execute('INSERT INTO youtube_acquisitions VALUES (?,?)', (manifest_sha, token))
    payload = dict(url=url, final_url=url, mime='video/mp4', body_sha=merged['body_sha'],
                   fetched=time.time(), youtube_sha=manifest_sha)
    from .youtube_audit import verify
    verify(db, payload, job)
    return extract_video(db, payload)


def capture(db, token, url, cached):
    from .evidence import save_capture
    payload = cached if cached and cached.get("youtube_sha") else acquire(db, token, url)
    return save_capture(db, token, payload)
