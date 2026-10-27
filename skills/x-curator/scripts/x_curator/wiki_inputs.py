"""Only audited publication revisions enter the current knowledge catalog."""
from .stage_timings import timed
import json

from .wiki_projection import assemble
from .wiki_sources import sources
from .wiki_admission import historical,accepted_mapping


def mappings(db,current,runs=None):
    return mapping_snapshot(db,current,runs)[0]


@timed("wiki.mapping_validation",scope="corpus")
def mapping_snapshot(db,current,runs=None):
    selected=None if runs is None else json.dumps(runs)
    previous=set(historical(db).get('policy',{}).get('mapping_runs',()))
    rows=db.execute("""SELECT id FROM wiki_runs WHERE state='accepted'
        AND (? IS NULL OR id IN (SELECT value FROM json_each(?))) ORDER BY started,id""",(selected,selected))
    packets={row['id']:accepted_mapping(db,row['id'],previous) for row in rows}
    return assemble(current,packets),packets


def members(db, root, identities, current, pages):
    if current is None:
        return sources(db, root, identities), None
    selected = {key: current[key] for key in identities if key in current}
    return selected, pages if len(selected) == len(current) else None
