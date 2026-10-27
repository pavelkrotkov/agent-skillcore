"""Stage aggregates, overlap-aware timing and slow-item rankings."""
from collections import defaultdict
from .stage_stats import statistics, union_seconds

def slowest(rows):
    children = {row['parent'] for row in rows if row['parent']}
    leaves = [row for row in rows if row['elapsed'] is not None and row['id'] not in children]
    ordered = sorted(leaves, key=lambda row: row['elapsed'], reverse=True)
    return ordered[:10], list(filter(lambda row: row['context'].get('item'), ordered))[:10]



def audit_summary(groups):
    return [dict(phase=row['context'].get('phase'), publications=row['context'].get('publications'),
                 elapsed_seconds=row['elapsed'], outcome=row['outcome'])
            for row in groups['wiki.source_audit']]



def waits(groups):
    locks = groups['wiki.lock_and_index'] + groups['wiki.lock_and_activate']
    return dict(queue_wait_seconds=sum(row['context'].get('queue_wait_seconds', 0) for row in groups['worker.item']),
                lock_wait_seconds=sum(row['context'].get('lock_wait_seconds', 0) for row in locks),
                retries=sum(row['context'].get('attempt_number', 1) > 1 for row in groups['worker.item']))



def timing_summary(rows, groups):
    complete = all(row['finished'] is not None for row in rows)
    roots = [row for row in rows if row['parent'] is None]
    return dict(state='complete' if complete else 'incomplete',
                wall_seconds=max((row['elapsed'] for row in roots), default=None) if complete else None,
                local_processing_union_seconds=union_seconds(rows), **waits(groups))



def summarize(rows):
    groups = defaultdict(list)
    for row in rows:
        groups[row['stage']].append(row)
    slow, items = slowest(rows)
    return dict(stages=rows, aggregates={name: statistics(value) for name, value in sorted(groups.items())},
                slowest=slow, slow_items=items, corpus_audits=audit_summary(groups),
                **timing_summary(rows, groups))
