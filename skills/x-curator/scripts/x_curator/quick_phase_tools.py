"""The controller, rather than a prompt, restricts tools to each execution phase."""
import json
from . import native_search_trace, native_search_proof, quick_tool_proof


def native_limit(db, token):
    from .native_search import enabled, current
    row = db.execute('''SELECT e.input FROM executions f JOIN executions e
        ON e.id=json_extract(f.input,'$.phase.evidence_execution') AND e.token=f.token
        WHERE f.token=? AND e.role='factcheck_evidence' AND json_extract(f.input,'$.phase.name')='final'
        ORDER BY f.started DESC,f.id DESC LIMIT 1''', (token,)).fetchone()
    return None if current(db, token) or (row and enabled(json.loads(row['input']))) else 3


def selected(default, native, linked, phase):
    if phase == 'final' or linked:
        return ['validate']
    if phase == 'evidence':
        return ['read'] if native else ['search', 'read']
    return ['read', 'validate'] if native else default


def allowance(check, execution, request):
    if 'phase' in request and request['phase'].get('name') != 'final':
        raise ValueError('evidence phase is not a publication verdict')
    if request.get('phase', {}).get('name') != 'final':
        native_search_proof.allowance(check, execution, request)


def observed(db, token, execution, request, seen):
    final = request.get('phase', {}).get('name') == 'final'
    if final:
        from .quick_phase_proof import verify
        verify(db, token, request, execution)
        denied = native_search_trace.searches(execution['log']) or db.execute('''SELECT 1 FROM quick_tools WHERE
            token=? AND created>=? AND name IN ('search','read') AND json_extract(output,'$.isError')=0 LIMIT 1''',
            (token, execution['started'])).fetchone()
        if denied:
            raise ValueError('finalization attempted fresh evidence acquisition')
    quick_tool_proof.dynamic(db, token, execution['log'], seen, execution['started'] if final else 0)
