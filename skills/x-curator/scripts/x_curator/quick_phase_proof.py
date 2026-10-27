"""An interrupted evidence phase is input proof, never a completed publication verdict."""
import json

from . import model_trace, native_search, native_search_proof, native_search_trace, quick_tool_proof
from .receipts import digest, encoded
from .storage import sha256


def phase(db, token, request):
    row = db.execute("SELECT * FROM executions WHERE id=? AND token=? AND role='factcheck_evidence'",
                     (request['phase']['evidence_execution'], token)).fetchone()
    if row is None or row['finished'] is None or row['output'] is None:
        raise ValueError('missing completed evidence-phase receipt')
    initial, receipt = json.loads(row['input']), json.loads(row['output'])
    actual = digest(initial), digest(receipt), sha256(row['log']), receipt['input_proof']['events'].encode(), receipt['ended']
    if actual != (row['input_sha'], row['output_sha'], row['log_sha'], row['log'], row['finished']):
        raise ValueError('tampered evidence-phase receipt')
    model_trace.verify_input(receipt['input_proof'], initial)
    return row, initial, receipt


def verify(db, token, request, execution=None):
    from .quick_phase_budget import verify as verify_budget
    from .media_presentations import verify as verify_media
    row, initial, receipt = phase(db, token, request)
    check = db.execute('SELECT * FROM quick_checks WHERE token=?', (token,)).fetchone()
    verify_budget(check, row, initial, request, receipt)
    if native_search.enabled(initial) and len(native_search_trace.usage(row['log'])['queries']) != check['searches']:
        raise ValueError('evidence-phase native search usage changed')
    if execution is not None and row['finished'] > execution['started']:
        raise ValueError('finalization overlaps evidence acquisition')
    verify_media(db, initial['bundle'], initial.get('image_presentations', []))
    seen = dict(initial['bundle']['captures'])
    quick_tool_proof.dynamic(db, token, encoded(receipt['input_proof']), seen, row['started'], row['finished'])
    if seen != request['bundle']['captures']:
        raise ValueError('finalization input differs from observed evidence-phase captures')
    native_search_proof.sources(initial, row['log'], seen)
    return initial
