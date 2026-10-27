"""Replay complete bounded audio chunks against the independently qualified profile."""
import json
import os
from pathlib import Path
from . import blobs, prepared_video_urls as video_scope
from .speech_protocol import validate as speech, transcript as text


def qualified(profile=None):
    config = json.loads(Path(os.environ['X_CURATOR_SPEECH_CONFIG']).read_text()) if profile is None else profile
    return {key:config[key] for key in ('engine_sha', 'model_sha')}


def validate(db, manifest, profile=None):
    if manifest.get('silent') is True:
        if manifest['parts']:
            raise ValueError('silent video cannot contain speech receipts')
        return 'Silent video; no audio track.'
    if manifest.get('caption_sha'):
        from .video_captions import text as captions
        return captions(blobs.read(db, manifest['caption_sha']), manifest['duration'])
    return speech_text(db, manifest, qualified(profile))


def speech_text(db, manifest, profile):
    if not manifest['parts']:
        raise ValueError('non-silent video requires observed audio chunks')
    parts, end = [], 0
    for part in manifest['parts']:
        receipt = json.loads(blobs.read(db, part['receipt_sha']))
        speech(receipt, blobs.read(db, part['audio_sha']), profile)
        if part['offset'] != end:
            raise ValueError('prepared audio has a gap or overlap')
        end += receipt['duration']
        parts.append(dict(offset=part['offset'], receipt=receipt))
    if abs(end-video_scope.coverage(manifest)) > .05:
        raise ValueError('prepared transcript coverage or text changed')
    return text(parts)
