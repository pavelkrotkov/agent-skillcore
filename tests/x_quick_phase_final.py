import json
from x_curator import quick_mcp
from x_quick_fixtures import native


def finish(case, request):
    case.final_calls += 1
    closed = quick_mcp.call(case.db, case.token, 'read', {'source': 'https://example.test/release'})
    case.assertIn('controller-owned final phase', closed['content'][0]['text'])
    case.at = case.started + 95
    accepted = quick_mcp.call(case.db, case.token, 'validate', {'decision': case.decision})
    case.at = case.started + 110
    return native(request, json.loads(accepted['content'][0]['text'])['final_answer'], [closed, accepted])
