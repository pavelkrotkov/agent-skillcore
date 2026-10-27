"""Coalesce publication arrivals without spending source attempts or model calls."""
from .stage_timings import timed
import json

from .publication_files import private_target
from .wiki import run as wiki
from . import queue, receipts, wiki_store


@timed("wiki.index_entry", scope="selected")
def run(db, root):
    queue.initialize(db)
    receipts.initialize(db)
    wiki_store.initialize(db)
    published = {row[0] for row in db.execute("""SELECT p.id FROM publications p JOIN jobs j
        ON j.account=p.account AND j.id=p.source WHERE p.state='published' AND j.state='published'""")}
    if published == previous(db, root):
        return {'state': 'idle', 'action': 'no publication catalog changes; freshness is not audited here'}
    return wiki(db, root, 0)


def previous(db, root):
    try:
        pointer = private_target(root, 'wiki/CURRENT.json')
        identity = json.loads(pointer.read_text())['generation'] if pointer.exists() else None
        row = db.execute('SELECT manifest FROM wiki_builds WHERE id=?', (identity,)).fetchone() if identity else None
        return set(json.loads(row[0])['sources']) if row else set()
    except (ValueError, KeyError, TypeError, OSError):
        return None
