"""Keep the verified active generation and two newest completed predecessors."""
import json
from .retention_files import target, old, remove
from .retention_generation import current, generation


def plan(db, root, identity):
    folder = target(root, 'wiki/builds')
    rows = [row[0] for row in db.execute('SELECT id FROM wiki_builds ORDER BY created DESC,id DESC') if generation(row[0])]
    completed = predecessors(root, rows, identity)
    keep = {identity, *completed[:2]}
    return obsolete(folder, keep, rows), [value for value in rows if value not in keep]


def predecessors(root, rows, identity):
    return [value for value in rows if value != identity
            and target(root, 'wiki/builds/' + value + '/site/index.html').is_file()]


def obsolete(folder, keep, records):
    paths = []
    for path in folder.iterdir():
        if generation(path.name) and path.name not in keep:
            if path.name in records or old(path):
                paths.append(path)
    return paths


def run(db, root, apply=False):
    identity = current(db, root)
    if identity is None:
        return dict(files=0, bytes=0, records=0)
    paths, records = plan(db, root, identity)
    # Interrupted deletion leaves missing directories; the next pass reconciles their rows.
    with db:
        if apply:
            db.execute('BEGIN IMMEDIATE')
            if json.loads(target(root, 'wiki/CURRENT.json').read_text())['generation'] != identity:
                raise ValueError('current wiki changed during retention')
        result = remove(root, paths, apply)
        if apply:
            db.executemany('DELETE FROM wiki_builds WHERE id=?', [(value,) for value in records])
    return dict(result, records=len(records))
