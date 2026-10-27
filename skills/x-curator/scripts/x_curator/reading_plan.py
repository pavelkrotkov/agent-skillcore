"""Versioned complete intervals; old policies remain immutable for publication audit."""
from .receipts import digest
from .reading_ranges import split
from .reading_plan_v2 import groups as page_groups
from .media_inputs import requires_partition as page_required

POLICIES = {1: {'width': 100000, 'context': 2000, 'max_segments': 16},
            2: {'width': 100000, 'context': 2000, 'max_segments': 16, 'images': 32},
            3: {'width': 200000, 'context': 2000, 'max_segments': 16}}
CURRENT_VERSION = 3


def plan(evidence, version=None):
    if version is None:
        version = 2 if page_required(evidence) else CURRENT_VERSION
    policy = POLICIES[version]
    parts = page_groups(evidence, policy) if version == 2 else groups(intervals(evidence, policy['width']), policy['width'])
    if len(parts) > policy['max_segments']:
        raise ValueError('source exceeds verified reading segment limit')
    return {'version': version, 'bundle_sha': digest(evidence), 'parts': parts}


def intervals(evidence, width):
    for key, capture in sorted(evidence['captures'].items()):
        for start, end in split(capture.get('text', ''), width):
            yield {'capture': key, 'start': start, 'end': end, 'capture_sha': digest(capture)}


def groups(spans, width):
    parts, current, size = [], [], 0
    for span in spans:
        length = span['end'] - span['start']
        if current and (size + length > width or span['capture'] in {p['capture'] for p in current}):
            parts.append(current)
            current, size = [], 0
        current.append(span)
        size += length
    return parts + [current]
