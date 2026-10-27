"""Keep repeated corpus-wide input audits explicit in the run journal."""
from . import wiki_inputs,proof_revisions
from .wiki_mapping_receipts import accepted_runs
from .stage_timings import span
from .audit_reuse import snapshot
from .read_set import ReadSet
from .receipts import digest


def load(db, root, phase):
    with span(db, 'wiki.input_loading', phase=phase, scope='corpus') as timing:
        current = wiki_inputs.sources(db, root)
        runs = accepted_runs(db)
        pages,packets = wiki_inputs.mapping_snapshot(db,current,runs)
        timing.update(publications=len(current), pages=len(pages))
    return (current,runs,pages),packets


class Snapshot:
    """One captured proof union; every activation and readback still rehashes it."""
    def __init__(self, db, root, phase='input', retained=None):
        self.db, self.root = db, root
        self.reads = ReadSet(db, shared=True)
        if retained is None:
            with snapshot(db):
                self.values,self.packets = load(self.reads, root, phase)
                self.stamp,self.epoch = self.reads.captured(),proof_revisions.epoch(db)
        else:
            payload,record=retained
            self.values,self.packets=payload['values'],payload['packets']
            self.reads.queries,self.reads.files=dict(record[1]),dict(record[2])
            self.stamp,self.reads.metadata,self.epoch=record[3],dict(record[4]),payload['epoch']
        self.binding = digest(self.values)
        self.previous_verified=False

    def check(self, db, root, sources, pages, runs):
        if db is not self.db or root != self.root or digest((sources, runs, pages)) != self.binding:
            raise ValueError('wiki proof snapshot does not match build inputs')
        return self.reads, self.stamp

    def build(self):
        from .wiki_build import build
        sources, runs, pages = self.values
        return build(self.db, self.root, sources, pages, runs, self)

    def current(self):
        from .wiki_input_fence import bound_current
        return bound_current(self)
