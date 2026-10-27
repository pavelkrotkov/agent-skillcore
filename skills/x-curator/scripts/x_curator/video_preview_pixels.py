"""Pixel-bound, hash-cached previews use the existing video decoder, never a new model."""
import struct
import subprocess

from .storage import sha256

VERIFIED = set()
POLICY = 'video-frame-preview-768/v1'


def dimensions(body):
    if len(body) < 24 or body[:8] != b'\x89PNG\r\n\x1a\n':
        raise ValueError('video preview requires an acquired PNG frame')
    size = struct.unpack('>II', body[16:24])
    if not 0 < size[0] * size[1] <= 32000000:
        raise ValueError('video frame dimensions exceed the decoding bound')
    return size


def scaled_size(size):
    edge = max(size)
    return tuple(max(1, n * 768 // edge) for n in size)


def convert(body, size, raw=False):
    width, height = size
    output = ['-f', 'rawvideo', '-pix_fmt', 'rgb24'] if raw else ['-f', 'image2pipe', '-vcodec', 'png', '-compression_level', '1']
    args = ['ffmpeg', '-v', 'error', '-protocol_whitelist', 'file,pipe', '-i', 'pipe:0',
            '-frames:v', '1', '-vf', f'scale={width}:{height}:flags=area', *output, 'pipe:1']
    return subprocess.run(args, input=body, capture_output=True, check=True, timeout=10).stdout


def remember(identity):
    if len(VERIFIED) >= 128:
        VERIFIED.clear()
    VERIFIED.add(identity)


def verify_pixels(original, preview, size):
    identity = sha256(original), sha256(preview), size, POLICY
    if identity not in VERIFIED:
        if convert(original, size, raw=True) != convert(preview, size, raw=True):
            raise ValueError('video preview pixels do not derive from the acquired frame')
        remember(identity)
