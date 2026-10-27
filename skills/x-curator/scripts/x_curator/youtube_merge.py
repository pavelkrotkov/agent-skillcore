"""Reproducible local-file merge retains its tool and probe receipts."""
import json
import subprocess
import tempfile
from pathlib import Path

from . import blobs


def merge(db, streams, duration):
    # ffmpeg sees content-addressed local files only; extractor URLs must never reach a subprocess.
    paths = ['blobs/' + stream['body_sha'] for stream in streams]
    args = ['ffmpeg', '-nostdin', '-v', 'error', '-protocol_whitelist', 'file,pipe', '-i', paths[0],
            '-protocol_whitelist', 'file,pipe', '-i', paths[1], '-map', '0:v:0', '-map', '1:a:0',
            '-c', 'copy', '-map_metadata', '-1', '-fflags', '+bitexact', '-flags:v', '+bitexact', '-flags:a', '+bitexact', '-n']
    with tempfile.TemporaryDirectory(dir=blobs.state_root(db)) as folder:
        target = Path(folder) / 'merged.mp4'
        subprocess.run(args + [str(target)], cwd=blobs.state_root(db), capture_output=True, check=True, timeout=60)
        probe = subprocess.run(['ffprobe', '-protocol_whitelist', 'file,pipe', '-v', 'error', '-show_format',
                                '-show_streams', '-of', 'json', str(target)], capture_output=True, check=True, timeout=30)
        validate_probe(json.loads(probe.stdout), duration)
        body_sha = blobs.put(db, target.read_bytes())
    version = subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True, timeout=10)
    return dict(body_sha=body_sha, probe_sha=blobs.put(db, probe.stdout), version_sha=blobs.put(db, version.stdout), args=args)


def validate_probe(metadata, duration):
    if {s['codec_type'] for s in metadata['streams']} != {'video', 'audio'}:
        raise ValueError('YouTube merge does not contain both audio and video')
    if abs(float(metadata['format']['duration']) - duration) >= 2:
        raise ValueError('YouTube media duration differs from metadata')


def verify_merge(db, merged, payload, duration, streams):
    if payload['body_sha'] != merged['body_sha']:
        raise ValueError('YouTube capture differs from controller merge')
    paths = ['blobs/' + stream['body_sha'] for stream in streams]
    inputs = [merged['args'][i + 1] for i, arg in enumerate(merged['args']) if arg == '-i']
    if inputs != paths:
        raise ValueError('YouTube merge input differs from acquired streams')
    blobs.read(db, merged['body_sha'])
    blobs.read(db, merged['version_sha'])
    validate_probe(json.loads(blobs.read(db, merged['probe_sha'])), duration)
