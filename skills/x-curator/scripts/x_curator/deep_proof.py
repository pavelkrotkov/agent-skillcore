"""Historical publication retains the exact consumed human permission and allowance."""
from . import deep_permission, deep_scope, deep_store, native_search, native_search_proof, quick_store


def allowance(db, token, execution, request):
    if request.get('policy') == quick_store.POLICY:
        from .quick_proof import allowance as quick_allowance
        check = db.execute('SELECT * FROM quick_checks WHERE token=?', (token,)).fetchone()
        return quick_allowance(check, execution, request)
    run = db.execute('SELECT * FROM deep_runs WHERE token=?', (token,)).fetchone()
    if run is None or request.get('policy') != deep_store.POLICY:
        raise ValueError('approved research run missing')
    permission, proposal = deep_permission.verified(db, run['id'])
    require_budget(run, permission, execution, request)
    require_request(run, permission, proposal, request)
    if native_search.enabled(request):
        native_search_proof.allowance(run, execution, request)


def require_request(run, permission, proposal, request):
    deep_scope.observed(permission, proposal, request['bundle'])
    expected = dict(approval=run['id'], deadline=run['deadline'], question=permission['question'], scope=permission['scope'],
                    resource=proposal.get('resource'), search_mode=proposal.get('search_mode'))
    if any(request.get(key) != value for key, value in expected.items()):
        raise ValueError('research ran outside its approved request')
    if (request['bundle']['account'], request['bundle']['source']) != (permission['account'], permission['source']):
        raise ValueError('research approval belongs to another source')


def require_budget(run, permission, execution, request):
    if permission['consumed'] != run['started'] or run['deadline'] != run['started'] + permission['seconds']:
        raise ValueError('approved allowance changed')
    if not run['started'] <= execution['started'] <= execution['finished'] <= run['deadline'] or (not native_search.enabled(request) and run['searches'] > 12):
        raise ValueError('approved research exceeded its allowance')
