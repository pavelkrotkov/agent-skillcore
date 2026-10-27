"""Retain timestamped WebVTT captions as fallible speech evidence, not verification."""
import html
import re
from datetime import datetime


def seconds(value):
    format = '%M:%S.%f' if value.count(':') == 1 else '%H:%M:%S.%f'
    return (datetime.strptime(value, format)-datetime(1900, 1, 1)).total_seconds()


def cue(block):
    lines = block.splitlines()
    timed = [i for i, line in enumerate(lines) if ' --> ' in line]
    if not timed:
        return None
    index = timed[0]
    start, end = [seconds(v.split()[0]) for v in lines[index].split(' --> ')]
    words = html.unescape(re.sub(r'<[^>]*>', '', ' '.join(lines[index+1:])))
    return start, end, words


def text(body, duration):
    source = body.decode('utf-8-sig').replace('\r\n', '\n')
    if not source.startswith('WEBVTT'):
        raise ValueError('caption body is not WebVTT')
    rows, previous = [], 0
    for start, end, words in filter(None, map(cue, source.split('\n\n'))):
        if not previous <= start <= end <= duration+.05:
            raise ValueError('caption timestamps are out of bounds')
        rows.append(f'[{start:.1f}-{end:.1f}] {words}')
        previous = start
    if not rows:
        raise ValueError('caption track contains no timed speech')
    return 'Machine captions; may contain errors.\n'+'\n'.join(rows)
