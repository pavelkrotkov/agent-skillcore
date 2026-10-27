"""Replay prepared media bytes, audio coverage and sampled-frame bindings offline."""
import json
import math
from . import blobs, video_transcript


def validate(db, payload, profile=None):
    blobs.verify_payload(db, payload)
    manifest = json.loads(blobs.read(db, payload['preparation_sha']))
    if (manifest['media_sha'], manifest['url']) != (payload['body_sha'], payload['url']):
        raise ValueError('prepared transcript belongs to different media')
    if not math.isfinite(manifest['duration']) or not 0 < manifest['duration'] <= 7200:
        raise ValueError('prepared video duration is invalid')
    if payload['text'] != video_transcript.validate(db, manifest, profile):
        raise ValueError('prepared transcript coverage or text changed')
    frames(payload, manifest)


def frames(payload, manifest):
    if not 0 < len(payload.get('frames', [])) <= 24:
        raise ValueError('prepared frames exceed the bounded attachment budget')
    if (payload['frames'], payload['images']) != (manifest['frames'], [f['sha'] for f in manifest['frames']]):
        raise ValueError('prepared frame images changed')
    if not all(valid_frame(f, manifest['duration']) for f in payload['frames']):
        raise ValueError('prepared frame timestamp is invalid')
    if not payload.get('limitations'):
        raise ValueError('machine transcription and sampled-frame limitations required')


def valid_frame(frame, seconds):
    return math.isfinite(frame['at']) and 0 <= frame['at'] <= seconds
