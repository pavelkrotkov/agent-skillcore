"""Bound video previews without discarding frames or changing acquired evidence."""
from . import blobs
from .media_presentation_schema import identities, video_images
from .video_preview_pixels import POLICY, convert, dimensions, remember, scaled_size, verify_pixels

LIMIT = ('Video frames were inspected as previews no larger than 768 pixels per edge; '
         'small text and fine details were not reliably observed.')


def prepare(db, evidence):
    records = []
    for original in sorted(video_images(evidence)):
        body = blobs.read(db, original)
        size = dimensions(body)
        if max(size) > 768:
            target = scaled_size(size)
            preview = convert(body, target)
            if dimensions(preview) != target:
                raise ValueError('video preview conversion returned incorrect dimensions')
            presented = blobs.put(db, preview)
            remember((original, presented, target, POLICY))
            records.append(dict(original=original, presented=presented, original_size=list(size),
                                presented_size=list(target), policy=POLICY))
    return records


def verify(db, evidence, records):
    identities(evidence, records)
    for record in records or []:
        original, preview = blobs.read(db, record['original']), blobs.read(db, record['presented'])
        if (dimensions(original), dimensions(preview)) != (tuple(record['original_size']), tuple(record['presented_size'])):
            raise ValueError('video preview dimensions differ from retained bytes')
        verify_pixels(original, preview, tuple(record['presented_size']))


def packet(db, request, decision, evidence):
    from .quick_packet import validate
    records = request.get('image_presentations', [])
    verify(db, request['bundle'], records)
    value = validate(decision, evidence)
    if value is not None and records:
        value['limitations'] = list(dict.fromkeys(value['limitations'] + [LIMIT]))
    return value
