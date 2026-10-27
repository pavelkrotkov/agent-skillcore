"""Bounded newline JSON-RPC transport shared by the curator's local tools."""
import json


def respond(message, tools, call):
    if message['method'] == 'tools/call':
        params = message['params']
        return call(params['name'], params.get('arguments', {}))
    return {'initialize': {'protocolVersion': '2024-11-05', 'capabilities': {'tools': {}},
                           'serverInfo': {'name': 'curator-check', 'version': '1'}},
            'tools/list': {'tools': tools}, 'ping': {}}[message['method']]


def serve(stream, output, handler, limit):
    for line in iter(lambda: stream.readline(limit + 1), ''):
        if len(line) > limit:
            raise ValueError('MCP request exceeds input limit')
        value = response(handler, line)
        if value is not None:
            print(json.dumps(value), file=output, flush=True)


def response(handler, line):
    identity = None
    try:
        message = json.loads(line)
        identity = message.get('id')
        if 'id' not in message:
            return None
        value = {'result': handler(message)}
    except (ValueError, KeyError, TypeError, AttributeError, OSError) as exc:
        code = {json.JSONDecodeError: -32700, AttributeError: -32600}.get(type(exc), -32602)
        value = {'error': {'code': code, 'message': str(exc)[:300]}}
    return dict(jsonrpc='2.0', id=identity, **value)
