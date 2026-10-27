"""The checker can only search or read controller-registered text sources."""
import time
import uuid

from . import native_search, quick_search, quick_web, quick_store, quick_packet, quick_tool_feedback
from .evidence import bundle
from .deadlines import until
from .receipts import encoded


def tools():
    return [dict(name=name, description=description, annotations={'readOnlyHint': True, 'destructiveHint': False, 'openWorldHint': True}, inputSchema={'type': 'object', 'properties': properties,
                'required': required, 'additionalProperties': False}) for name, description, properties, required in (
        ('search', 'Search once. Results are pointers, not factual proof. The controller enforces the request’s query allowance.', {'query': {'type': 'string'}}, ['query']),
        ('read', 'Read a bounded text excerpt; at most three public redirects. Missing match returns the start. No PDFs, video or transcription.',
         {'source': {'type': 'string', 'description': 'Exact URL from native search results, or a source ID/URL from curator search or the initial sources map. Search for unlisted URLs first.'}, 'match': {'type': 'string', 'maxLength': 200}}, ['source']),
        ('validate', 'Check a draft decision against captured evidence before final submission. Returns errors for correction; does not publish or extend any allowance.',
         {'decision': {'type': 'object'}}, ['decision']))]



def execute(db, token, name, arguments):
    from .quick_window import require_phase
    require_phase(db, token, name)
    schema = {tool['name']: tool['inputSchema'] for tool in tools()}[name]
    if not set(schema['required']) <= arguments.keys() <= schema['properties'].keys():
        raise ValueError('invalid tool arguments')
    if name == 'search':
        if native_search.current(db, token) is not None:
            raise ValueError('Use native web search for this quick check')
        return quick_search.search(db, token, arguments['query'])
    if name == 'read':
        native_search.register(db, token)
        return quick_web.read(db, token, arguments['source'], arguments.get('match', ''))
    quick_packet.validate(arguments['decision'], bundle(db, token))
    from .quick_final import receipt
    return receipt(db, token, arguments['decision'])


def call(db, token, name, arguments):
    identity = uuid.uuid4().hex
    with db:
        db.execute('INSERT INTO quick_tools(id,token,name,arguments,created) VALUES(?,?,?,?,?)',
                   (identity, token, name, encoded(arguments).decode(), time.time()))
    try:
        with until(quick_store.active(db, token)['deadline']):
            output = {'content': [{'type': 'text', 'text': encoded(execute(db, token, name, arguments)).decode()}], 'isError': False}
    except (ValueError, KeyError, TypeError, OSError) as exc:
        output = {'content': [{'type': 'text', 'text': str(exc)[:300]}], 'isError': True}
    quick_tool_feedback.append(db, token, output)
    with db:
        db.execute('UPDATE quick_tools SET output=?,finished=? WHERE id=?', (encoded(output).decode(), time.time(), identity))
    return output
