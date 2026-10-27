"""Private measured outcomes; missing timing receipts never become zero-duration success."""
from collections import Counter
import json

from . import batch_report, deep_store, native_search, stage_timings
from .policy_timings import measure
from .queue import counts as queue_counts


def report(db):
    batches = batch_report.report(db)['batches']
    runs = [measure(db, dict(r), 'check', native_search.limit(db, r['token'])) for r in db.execute('SELECT * FROM quick_checks ORDER BY started,id')]
    if deep_store.exists(db):
        runs.extend(measure(db, dict(r), 'approval', 12) for r in db.execute('SELECT d.*,p.account,p.source FROM deep_runs d JOIN research_permissions p ON p.id=d.id ORDER BY d.started,d.id'))
    counts = batch_counts(batches)
    return dict(state='checkpoint', historical_complete=False, cohort_counts=dict(counts), queue_counts=queue_counts(db), batches=batches, runs=runs, stage_timings=stage_timings.report(db),
                qualification='failed' if any(r['overruns'] for r in runs) else 'inspect_live_evidence',
                source_publication_latency_seconds=first_publication(db),
                note='Native searches count observed queries against a target of three, not a hard cap; unfinished executions can have additional unknown usage. Source admission timing is separate from a verified connected wiki; report audits the active wiki.')


def wiki_index_latency(db, manifest):
    sources = json.dumps(manifest['sources'])
    return db.execute("""SELECT b.created-max(e.finished) FROM wiki_builds b,publications p
        JOIN executions e ON e.id=p.review WHERE b.id=? AND p.id IN (SELECT value FROM json_each(?))""",
                      (manifest['generation'], sources)).fetchone()[0]


def first_publication(db):
    rows = db.execute("""SELECT p.id,a.finished,a.state FROM publications p
        JOIN executions e ON e.id=p.proposal JOIN attempts a ON a.token=e.token
        WHERE p.state='published' AND json_extract(e.input,'$.policy')='quick-factcheck/v1'""")
    completed = [completion(db, row) for row in rows]
    started = db.execute('SELECT min(started) FROM quick_checks').fetchone()[0]
    if not completed or None in completed or started is None:
        return None
    return min(completed) - started


def completion(db, row):
    from .publication_recovery_store import recovery
    receipt = recovery(db, row['id'])
    if receipt:
        return receipt['completed']
    return row['finished'] if row['state'] == 'published' else None


def batch_counts(batches):
    counts = Counter()
    for batch in batches:
        if batch['kind'] != 'research-review':
            counts.update(item['state'] for item in batch['items'])
    return counts
