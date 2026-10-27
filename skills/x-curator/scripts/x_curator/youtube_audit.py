"""Replay retained YouTube identity, range and assembly proofs without networking."""
import json

from . import blobs, youtube_resolver, youtube_redirects
from .youtube_player import selection
from .youtube_stream_audit import verify_stream
from .youtube_merge import verify_merge
from .youtube_urls import video_id


def verify(db, payload, job):
    manifest = json.loads(blobs.read(db, payload['youtube_sha']))
    row = db.execute('''SELECT a.account,a.id FROM youtube_acquisitions y
        JOIN attempts a ON a.token=y.token WHERE y.sha=?''', (payload['youtube_sha'],)).fetchone()
    if row is None or tuple(row) != (job['account'], job['id']):
        raise ValueError('YouTube acquisition belongs to a different source')
    identity = video_id(payload['url'])
    if (manifest['version'], manifest['resolver'], manifest['url'], manifest['video_id']) != (1, youtube_resolver.VERSION, payload['url'], identity):
        raise ValueError('YouTube acquisition identity differs')
    result = json.loads(blobs.read(db, manifest['result_sha']))
    selected = selection(db, result, manifest['receipts'], job, payload['url'])
    if [stream['format'] for stream in manifest['streams']] != selected:
        raise ValueError('YouTube stream selection differs from resolver result')
    for stream in manifest['streams']:
        verify_stream(db, stream, job)
    verify_merge(db, manifest['merge'], payload, result['duration'], manifest['streams'])


def verify_bundle(db, captures, job):
    for payload in captures.values():
        youtube_redirects.validate(payload)
        if payload.get("youtube_sha"):
            verify(db, payload, job)
