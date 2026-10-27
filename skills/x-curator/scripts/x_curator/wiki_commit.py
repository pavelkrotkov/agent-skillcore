"""Replay source dependencies and activate one verified wiki generation."""
import time
from . import wiki_inputs,proof_revisions
from .wiki_input_fence import verify
from .read_set import ReadSet
from .receipts import digest, encoded
from .wiki_files import activate, verify_generation
from .wiki_mapping_receipts import accepted_runs
from .stage_timings import span

def commit(db, root, identity, manifest, sources, pages, runs, snapshot=None):
    with span(db, 'wiki.precommit_replay', phase='precommit', scope='corpus', publications=len(sources)):
        reads, stamp = (snapshot.check(db, root, sources, pages, runs) if snapshot is not None
                        else replay(db, root, sources, pages, runs))
    with span(db, 'wiki.lock_and_activate', scope='corpus', generation=identity) as timing:
        began = time.monotonic()
        with db:
            db.execute('BEGIN IMMEDIATE')
            timing['lock_wait_seconds'] = time.monotonic()-began
            verify(reads,stamp,snapshot)
            with span(db,'wiki.link_validation',scope='corpus'):
                artifacts = verify_generation(root, manifest)
            if snapshot is not None:
                snapshot.artifacts=artifacts
            db.execute('INSERT OR IGNORE INTO wiki_builds VALUES (?,?,?)', (identity, encoded(manifest).decode(), time.time()))
            activate(root, identity)
            if snapshot is not None:
                snapshot.epoch=proof_revisions.epoch(db)


def replay(db, root, sources, pages, runs):
    with db:
        db.execute('BEGIN DEFERRED')
        reads = ReadSet(db, shared=True)
        latest = wiki_inputs.sources(reads, root, sources)
        if digest(latest) != digest(sources) or accepted_runs(reads) != runs or digest(wiki_inputs.mappings(reads, latest, runs)) != digest(pages):
            raise ValueError('wiki inputs changed during build; rebuild accepted mappings')
        return reads, reads.captured()
