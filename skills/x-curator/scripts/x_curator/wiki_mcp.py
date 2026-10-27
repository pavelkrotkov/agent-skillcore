"""Read-only draft validation for the existing wiki organization execution."""
from contextlib import closing
from functools import partial
from pathlib import Path
import sqlite3
import sys

from . import mcp_stdio, wiki_context, wiki_draft
from .deadlines import until


def respond(db, identity, message):
    def call(name, arguments):
        if name == 'context':
            return wiki_context.call(db, identity, arguments)
        return wiki_draft.call(db, identity, name, arguments)
    return mcp_stdio.respond(message, [*wiki_draft.tools(), wiki_context.tool()], call)


def serve(db, identity, stream, output):
    with until(wiki_draft.active(db, identity)['expires']):
        mcp_stdio.serve(stream, output, partial(respond, db, identity), 1000000)


if __name__ == '__main__':
    path = (Path(sys.argv[1]) / 'curator.sqlite3').resolve()
    with closing(sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)) as store:
        store.row_factory = sqlite3.Row
        serve(store, sys.argv[2], sys.stdin, sys.stdout)
