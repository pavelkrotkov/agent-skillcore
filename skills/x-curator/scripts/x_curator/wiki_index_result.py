"""Generation result accounting and checkpoint publication share one path."""
from .policy_metrics import wiki_index_latency
from . import wiki_checkpoint, retention_wiki
from .wiki_files import verify_generation


def report(db, manifest, current, pages):
    mapped = {ref['publication'] for page in pages.values() for ref in page['claims']}
    return {'state': 'checkpoint', 'generation': manifest['generation'], 'verified_sources': len(current),
            'mapped_sources': len(mapped), 'unmapped_sources': len(current) - len(mapped), 'pages': len(pages),
            'verdict_to_index_seconds': wiki_index_latency(db, manifest)}



def publish(db,root,snapshot):
    current,_,pages=snapshot.values
    if not current:
        return {'state':'empty','sources':0}
    manifest=snapshot.build()
    retained=retention_wiki.run(db,root,apply=True)
    if retained['files']:
        snapshot.artifacts=verify_generation(root,manifest)
    result=report(db,manifest,current,pages)
    wiki_checkpoint.save(db,root,snapshot,manifest,result)
    return result

def command(db,args):
    from .wiki import run
    from .proof_mode import audit
    with audit(getattr(args,'audit',False)):
        return run(db,args.state,0 if getattr(args,'audit',False) else args.max_sources)
