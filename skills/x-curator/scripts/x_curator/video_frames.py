"""Seek sampling retains its actual positions when container tails lack frames."""
import subprocess

from . import blobs


def sample_frames(db, path, duration):
    frames = []
    for index in range(6):
        at, body = recover_frame(path, duration * (index + 0.5) / 6)
        frames.append({"at": at, "sha": blobs.put(db, body)})
    return frames


def recover_frame(path, requested):
    for at in (requested, requested * 0.8, 0):
        result = subprocess.run(["ffmpeg", "-protocol_whitelist", "file,pipe", "-v", "error", "-ss", str(at), "-i", str(path),
                                 "-frames:v", "1", "-vf", "scale=960:-1", "-f", "image2pipe", "-vcodec", "png", "-"],
                                capture_output=True, check=True, timeout=45)
        if result.stdout:
            return at, result.stdout
    raise ValueError("video frame recovery failed")
