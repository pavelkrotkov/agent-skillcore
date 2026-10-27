"""Per-execution stdio tools with controller-owned source IDs, counters and deadline."""
from functools import partial
import sys

from . import mcp_stdio, native_search, quick_store
from .deadlines import until
from .storage import open_store
from .quick_tool_schema import tools, call


def respond(db, token, message):
    available = tools()
    if native_search.current(db, token) is not None:
        available = [tool for tool in available if tool['name'] != 'search']
    return mcp_stdio.respond(message, available, partial(call, db, token))


def serve(db, token, stream, output):
    with until(quick_store.active(db, token)['deadline']):
        mcp_stdio.serve(stream, output, partial(respond, db, token), 65536)


if __name__ == '__main__':
    with open_store(sys.argv[1]) as store:
        serve(store, sys.argv[2], sys.stdin, sys.stdout)
