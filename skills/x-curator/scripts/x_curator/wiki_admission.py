"""Previously committed sources require proof seals or explicit historical maintenance."""
import json
from .audit_reuse import connection
from .proof_mode import FULL


def historical(db):
    if FULL.get():
        return {}
    raw=connection(db)
    if not raw.execute("SELECT 1 FROM sqlite_master WHERE name='wiki_builds'").fetchone():
        return {}
    row=raw.execute('SELECT manifest FROM wiki_builds ORDER BY created DESC,id LIMIT 1').fetchone()
    return json.loads(row[0]) if row else {}


def accepted_mapping(db,identity,previous):
    from .audit_reuse import cached
    from .blobs import state_root
    from .wiki_mapping_receipts import verified
    return cached(db,state_root(db),('mapping',identity),lambda reads: verified(
        reads.execute('SELECT * FROM wiki_runs WHERE id=?',(identity,)).fetchone())[1],required=identity in previous)


def historical_sources(db):
    from .proof_revision_state import state
    state(connection(db))
    return set(historical(db).get('sources',()))
