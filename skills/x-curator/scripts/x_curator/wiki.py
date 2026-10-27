"""Bounded organization is independent of deterministic wiki rebuilding."""
from .wiki_index_result import report,publish
from .wiki_mapping import organize
from .wiki_input_load import Snapshot
from .wiki_current import current as current_generation
from .stage_timings import timed, skip
from . import wiki_store,wiki_checkpoint,proof_revisions


@timed('wiki.pipeline', scope='corpus')
def run(db, root, max_sources=5):
    if not 0 <= max_sources <= 10:
        raise ValueError('wiki batch must contain between zero and ten sources')
    snapshot,result=initial(db,root)
    current,_,pages=snapshot.values
    if result is None:
        if not snapshot.previous_verified:
            reconcile(db,root,current,pages)
        result=publish(db,root,snapshot)
    if not (selected:=candidates(db,current)[:max_sources]):
        skip(db,'wiki.organization','no selected mapping candidates')
        return result
    if action:=organize(db,current,pages,selected):
        return dict(result,state='blocked',action=action)
    proof_revisions.prepare(db)
    return publish(db,root,Snapshot(db,root,'post_mapping'))


def initial(db,root):
    wiki_store.initialize(db)
    try:
        proof_revisions.prepare(db)
        retained=wiki_checkpoint.restore(db,root)
        return retained if retained else (Snapshot(db,root),None)
    except (ValueError,OSError,KeyError,TypeError,RuntimeError):
        reconcile(db,root)
        raise


def candidates(db, current):
    excluded = {row[0] for row in db.execute("""SELECT publication FROM wiki_sources WHERE run IS NOT NULL OR
        attempts>=3+(SELECT count(*) FROM wiki_recovery_grants WHERE publication=wiki_sources.publication)""")}
    return sorted(set(current) - excluded)


@timed('wiki.reconciliation', scope='corpus')
def reconcile(db, root, sources=None, pages=None):
    try:
        return current_generation(db, root, sources, pages)
    except (ValueError, OSError, KeyError, TypeError, RuntimeError):
        return None
