"""Import an explicitly approved controller extraction, never model-authored evidence."""
import json
from pathlib import Path

from . import blobs, prepared_video, video_transcript, prepared_video_urls as video_scope
from .receipts import encoded


def body(root, name):
    path = (root / name).resolve()
    if root not in path.parents or not path.is_file() or path.stat().st_size > 128*1024*1024:
        raise ValueError('video package file escapes its bounded directory')
    return path.read_bytes()


def ingest(db, account, source, folder, reason):
    root = Path(folder).resolve()
    manifest = json.loads(body(root, 'package.json'))
    if (manifest['account'], manifest['source']) != (account, source):
        raise ValueError('foreign video package')
    if manifest['revision'] != prepared_video.revision(db, dict(account=account, id=source)):
        raise ValueError('video package source revision changed during preparation')
    manifest['media_sha'] = blobs.put(db, body(root, manifest.pop('media_file')))
    if manifest.get('caption_file'):
        manifest['caption_sha'] = blobs.put(db, body(root, manifest.pop('caption_file')))
    for frame in manifest['frames']:
        frame['sha'] = blobs.put(db, body(root, frame.pop('file')))
    for part in manifest['parts']:
        part['audio_sha'] = blobs.put(db, body(root, part.pop('audio_file')))
        part['receipt_sha'] = blobs.put(db, body(root, part.pop('receipt_file')))
    payload = dict(kind='video', url=manifest['url'], body_sha=manifest['media_sha'], fetched=manifest.get('fetched', 0),
                   preparation_sha=blobs.put(db, encoded(manifest)), text=video_transcript.validate(db, manifest),
                   frames=manifest['frames'], images=[f['sha'] for f in manifest['frames']],
                   limitations=['Machine transcription can contain errors; verify important quotations against audio.',
                                'Visual evidence is sampled frames, not continuous motion or proof of efficacy.']+video_scope.limitations(manifest))
    return prepared_video.store(db, dict(account=account, id=source), payload, reason)
