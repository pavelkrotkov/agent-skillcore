"""Append accepted arrivals to a freshly fenced catalog without replaying old receipts."""
from . import proof_revisions
from .wiki_sources import sources
from .wiki_projection import assemble
from .receipts import digest
from .stage_timings import span


def append(snapshot,live):
    prior=snapshot.values[0]
    if not set(prior)<=live:
        return None
    with span(snapshot.db,'wiki.input_loading',phase='incremental',scope='selected',publications=len(live-set(prior))):
        current=dict(prior)
        current.update(sources(snapshot.reads,snapshot.root,live-set(prior)))
        snapshot.values=current,snapshot.values[1],assemble(current,snapshot.packets)
        snapshot.stamp,snapshot.epoch=snapshot.reads.captured(),proof_revisions.epoch(snapshot.db)
        snapshot.binding=digest(snapshot.values)
        snapshot.artifacts={}
    return snapshot,None
