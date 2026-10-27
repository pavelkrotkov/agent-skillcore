"""Reconstruct audited source revisions and their citation provenance."""
import json

from .publication_audit import verify_publication
from .stage_timings import span
from .read_set import ReadSet
from .wiki_admission import historical_sources


def sources(db, root, publications=None):
    result = {}
    rows = selected(db, publications)
    previous=historical_sources(db)
    with span(db, 'wiki.source_audit', scope='corpus' if publications is None else 'selected',
              publications=len(rows), bytes=sum(len(row['body']) for row in rows)):
        for row in rows:
            packet, evidence = verify_publication(db, root, row,required=row['id'] in previous)
            provenance = {key: {'url': c['url'], 'fetched': c.get('fetched'), 'sha': c.get('body_sha')} for key, c in evidence['captures'].items()}
            result[row['id']] = {'packet': packet, 'created': row['created'], 'source': row['source'], 'sha': row['sha'], 'provenance': provenance}
    return result


def selected(db, publications):
    query = "SELECT p.* FROM publications p JOIN jobs j ON j.account=p.account AND j.id=p.source WHERE p.state='published' AND j.state='published'"
    if publications is None and isinstance(db, ReadSet):
        publications = [row[0] for row in db.db.execute(query.replace('p.*', 'p.id'))]
    parameters = ()
    if publications is not None:
        query += ' AND p.id IN (SELECT value FROM json_each(?))'
        parameters = (json.dumps(list(publications)),)
    return db.execute(query, parameters).fetchall()
