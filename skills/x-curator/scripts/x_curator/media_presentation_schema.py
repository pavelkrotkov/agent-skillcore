"""Bind preview identities to original video frames in the original attachment order."""
from .media_inputs import identities as acquired
from .video_preview_pixels import POLICY, scaled_size


def video_images(evidence):
    return {image for capture in evidence['captures'].values() if capture.get('prepared_video')
            for image in capture.get('images', [])}


def identities(evidence, records=None):
    mapping = {}
    allowed = video_images(evidence)
    for record in records or []:
        original = record['original']
        if original not in allowed or original in mapping:
            raise ValueError('video preview has a foreign or repeated original')
        validate_record(record)
        mapping[original] = record['presented']
    return [mapping.get(original, original) for original in sorted(acquired(evidence))]


def validate_record(record):
    size, target = record['original_size'], record['presented_size']
    validate_size(size)
    validate_size(target)
    if record['policy'] != POLICY or max(size) <= 768 or tuple(target) != scaled_size(size):
        raise ValueError('video preview policy or dimensions changed')


def validate_size(size):
    if len(size) != 2 or any(type(n) is not int or n < 1 for n in size):
        raise ValueError('video preview dimensions must be positive integer pairs')
