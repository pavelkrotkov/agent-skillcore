"""Speech receipts bind a complete mono PCM input to a pinned executable and model."""
import time

from .storage import sha256

from .speech_audio import duration


def validate(receipt, body, config):
    seconds = duration(body)
    if (receipt['engine_sha'], receipt['model_sha']) != (config['engine_sha'], config['model_sha']):
        raise ValueError('speech reader differs from qualified profile')
    if (receipt['audio_sha'], receipt['duration']) != (sha256(body), seconds):
        raise ValueError('speech receipt belongs to different audio')
    for segment in receipt['segments']:
        validate_segment(segment, seconds)
    return receipt

def make_receipt(output, config, body, seconds, started):
    segments = [{'start': s['offsets']['from'] / 1000, 'end': s['offsets']['to'] / 1000, 'text': s['text'].strip()}
                for s in output['transcription']]
    if segments and segments[-1]['end'] <= seconds + 30:
        segments[-1]['end'] = min(segments[-1]['end'], seconds)
    return {'engine': 'whisper.cpp v1.9.4', 'model': 'small', 'engine_sha': config['engine_sha'],
            'model_sha': config['model_sha'], 'audio_sha': sha256(body), 'duration': seconds,
            'started': started, 'finished': time.time(), 'segments': segments}


def validate_segment(segment, seconds):
    if not 0 <= segment['start'] <= segment['end'] <= seconds + 1:
        raise ValueError('speech segment lies outside input')
    if not isinstance(segment['text'], str):
        raise ValueError('speech segment must be text')


def transcript(parts):
    return 'Machine transcript; may contain errors.\n' + '\n'.join(
        f"[{s['start']+part['offset']:.1f}-{s['end']+part['offset']:.1f}] {s['text']}"
        for part in parts for s in part['receipt']['segments'])
