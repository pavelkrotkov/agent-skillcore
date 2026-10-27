"""Compute median, p95 and inclusive process CPU for stage invocations."""
from collections import Counter
from statistics import median
import math

from .stage_intervals import union_seconds
from .stage_liveness import interrupted

_STATES = ('completed', 'failed', 'timeout', 'interrupted', 'running', 'unverified', 'skipped')


def measured(row):
    return row['elapsed'] is not None and row['outcome'] != 'skipped'


def percentiles(values):
    if not values:
        return dict(median_seconds=None, p95_seconds=None)
    return dict(median_seconds=median(values),
                p95_seconds=values[math.ceil(.95*len(values)) - 1])


def statistics(rows):
    completed = list(filter(measured, rows))
    values = sorted(row['elapsed'] for row in completed)
    counts = Counter(row['outcome'] for row in rows)
    return dict(invocations=len(rows), samples=len(values),
                outcomes={state: counts[state] for state in _STATES},
                total_invocation_seconds=sum(values),
                process_cpu_seconds_inclusive=sum(row['process_cpu_seconds'] or 0 for row in completed),
                **percentiles(values))
