"""Current knowledge is withdrawn when its sources, mappings or artifacts change."""
import json

from . import wiki_inputs
from .receipts import digest
from .publication_files import private_target
from .wiki_files import activate, verify_generation
from .wiki_mapping_receipts import accepted_runs
from .stage_timings import span, timed


def current(db, root, sources=None, pages=None):
    """Supplied snapshots must be freshly audited in the same synchronous phase."""
    if not (pointer := private_target(root, 'wiki/CURRENT.json')).exists():
        return None
    try:
        if (identity := json.loads(pointer.read_text())['generation']) is None:
            return None
        return checked_current(db, root, identity, sources, pages)
    except (ValueError, OSError, KeyError, TypeError, RuntimeError):
        activate(root, None)
        raise


@timed('wiki.current_readback', scope='corpus', phase='readback')
def checked_current(db, root, identity, sources=None, pages=None):
    if (row := db.execute('SELECT manifest FROM wiki_builds WHERE id=?', (identity,)).fetchone()) is None:
        raise ValueError('current wiki has no build receipt')
    manifest = json.loads(row[0])
    latest, pages = wiki_inputs.members(db, root, manifest['sources'], sources, pages)
    if set(latest) != set(manifest['sources']) or digest(latest) != manifest['policy']['sources']:
        raise ValueError('current wiki source set is stale')
    runs = manifest['policy'].get('mapping_runs')
    if pages is None or runs not in (None, accepted_runs(db)):
        pages = wiki_inputs.mappings(db, latest, runs)
    if digest(pages) != manifest['policy']['mappings']:
        raise ValueError('current wiki mappings are stale')
    with span(db, 'wiki.final_files', scope='corpus', generation=identity, files=len(manifest['files'])):
        verify_generation(root, manifest)
    return manifest
