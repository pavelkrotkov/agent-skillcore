"""Accept bounded mono PCM audio with a declared duration suitable for transcription."""
import io
import wave
import time

from .deadlines import until

MAX_AUDIO = 58 * 1024 * 1024


def duration(body):
    if not 0 < len(body) <= MAX_AUDIO:
        raise ValueError('audio exceeds bounded reader input')
    with wave.open(io.BytesIO(body), 'rb') as audio:
        if (audio.getnchannels(), audio.getsampwidth(), audio.getframerate()) != (1, 2, 16000):
            raise ValueError('speech input must be mono PCM16 at 16kHz')
        frames = audio.getnframes()
        if len(audio.readframes(frames)) != frames * 2:
            raise ValueError('truncated PCM audio')
        seconds = frames / audio.getframerate()
    if not 0 < seconds <= 1800:
        raise ValueError('speech duration exceeds reader bound')
    return seconds


def read(stream, length):
    if not 0 < length <= MAX_AUDIO:
        raise ValueError('invalid speech request size')
    with until(time.time() + 60):
        body = stream.read(length)
    if len(body) != length:
        raise ValueError('incomplete speech request')
    return body
