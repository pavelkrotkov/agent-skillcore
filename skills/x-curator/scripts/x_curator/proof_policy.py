"""Invalidate proofs for their verifier dependency closure, not unrelated installed code."""
import ast
from functools import lru_cache
from pathlib import Path
import sys

ROOTS={'publication':('publication_audit',),'mapping':('wiki_mapping_receipts',),
       'wiki-render':('wiki_site','wiki_render','wiki_links','wiki_markdown'),'wiki-checkpoint':('wiki',),'wiki-links':('wiki_links',),'wiki-artifacts':('wiki_files','wiki_links')}


def imports(tree):
    local,external=set(),set()
    for node in ast.walk(tree):
        if isinstance(node,ast.ImportFrom):
            target=local if node.level else external
            target.update(from_names(node))
        elif isinstance(node,ast.Import):
            external.update(item.name.split('.')[0] for item in node.names)
    return local,external


@lru_cache(maxsize=8)
def dependencies(kind):
    folder=Path(__file__).parent
    pending=list(ROOTS.get(kind,tuple(p.stem for p in folder.glob('*.py'))))
    paths,external={},set()
    while pending:
        name=pending.pop()
        if name in paths or not (path:=folder/(name+'.py')).is_file():
            continue
        paths[name]=path
        local,other=imports(ast.parse(path.read_text()))
        pending.extend(local-paths.keys())
        external.update(other-sys.stdlib_module_names)
    return tuple(sorted(paths.values())),external


def from_names(node):
    return [node.module.split('.')[0]] if node.module else [item.name for item in node.names]
