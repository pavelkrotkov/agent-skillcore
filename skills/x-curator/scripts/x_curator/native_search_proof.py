"""Replay native query usage and URL admission from retained executor evidence."""
from . import native_search, native_search_trace


def allowance(check, execution, request):
    if native_search.enabled(request):
        observed = native_search_trace.usage(execution['log'])
        if observed['unfinished'] or check['searches'] != len(observed['queries']):
            raise ValueError('native search usage differs from executor receipt')
    elif check['searches'] > 3:
        raise ValueError('fact-check exceeded its durable allowance')


def sources(request, log, captures):
    if not native_search.enabled(request):
        return
    allowed = set(request['sources'].values()) | native_search_trace.urls(log)
    dynamic = captures.keys() - request['bundle']['captures'].keys()
    if any(captures[key]['requested_url'] not in allowed for key in dynamic):
        raise ValueError('read URL absent from retained native search results and initial sources')
