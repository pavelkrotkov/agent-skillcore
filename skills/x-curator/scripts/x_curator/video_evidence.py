"""Sampled frames plus machine transcription; neither is labelled a perfect transcript."""
import json
import subprocess
import sys
import os

from . import blobs
from .video_frames import sample_frames


def extract_video(db, payload):
    path = blobs.state_root(db) / "blobs" / payload["body_sha"]
    info = subprocess.run(["ffprobe", "-protocol_whitelist", "file,pipe", "-v", "quiet", "-show_format", "-show_streams", "-of", "json", str(path)],
                          capture_output=True, check=True, timeout=30)
    metadata = json.loads(info.stdout)
    duration = float(metadata["format"]["duration"])
    if not 0 < duration <= 1800:
        raise ValueError("video needs segmented recovery beyond current duration budget")
    frames = sample_frames(db, path, duration)
    text = "Silent video."
    speech = None
    if any(stream["codec_type"] == "audio" for stream in metadata["streams"]):
        result = subprocess.run([sys.executable, "-m", "x_curator.transcribe", str(path)],
                                capture_output=True, check=True, timeout=600)
        text = result.stdout.decode()
        if os.environ.get('X_CURATOR_SPEECH_CONFIG'):
            speech = json.loads(text)
            text = '\n'.join(f"[{s['start']:.1f}-{s['end']:.1f}] {s['text']}" for s in speech['segments'])
    return dict(payload, kind="video", text="Machine transcript; may contain errors. " + text,
                images=[frame["sha"] for frame in frames], frames=frames, speech=speech,
                limitations=["Visual evidence consists of six sampled frames; transcription is automated."])
