"""Native search keeps its actual usage and source pointers, never body evidence."""
import json

from . import blobs, native_search_trace, quick_sources

MODE = 'codex-native/three-query-target-v1'
RESEARCH_MODE = 'codex-native/twelve-query-target-v1'


def enabled(request):
    return (request.get('search_mode'), request.get('policy')) in (
        (MODE, 'quick-factcheck/v1'), (RESEARCH_MODE, 'approved-research/v1'), (MODE, 'zk-organization/v1'))


def current(db, token):
    row = db.execute("SELECT input,input_sha FROM executions WHERE token=? AND role IN ('factcheck','factcheck_evidence') ORDER BY started DESC,id DESC LIMIT 1", (token,)).fetchone()
    return row if row and enabled(json.loads(row['input'])) else None


def record(db, identity, log):
    row = db.execute('SELECT input,token FROM executions WHERE id=?', (identity,)).fetchone()
    request = json.loads(row['input'])
    if enabled(request):
        table = 'deep_runs' if request['policy'] == 'approved-research/v1' else 'quick_checks'
        with db:
            db.execute(f'UPDATE {table} SET searches=? WHERE token=?', (len(native_search_trace.usage(log)['queries']), row['token']))


def register(db, token):
    row = current(db, token)
    if row is None:
        return
    for url in native_search_trace.urls((blobs.state_root(db) / 'runs' / token / (row['input_sha'] + '.jsonl')).read_bytes()):
        try:
            quick_sources.source(db, token, url)
        except ValueError:
            continue


def limit(db, token):
    from .quick_phase_tools import native_limit
    return native_limit(db, token)


def research_mode(proposal):
    mode = proposal.get('search_mode')
    if mode not in (None, RESEARCH_MODE):
        raise ValueError('unsupported approved research search mode')
    return mode
