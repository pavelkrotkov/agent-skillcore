"""An immutable wiki generation becomes current only after source and file readback."""
import json

from .wiki_markdown import write as write_markdown
from .receipts import digest
from .audit_seal import policy
from .storage import sha256
from . import wiki_links
from .wiki_files import file_manifest, cached
from .wiki_mapping_receipts import accepted_runs
from .wiki_render import render
from .wiki_site import render_site
from .stage_timings import span, timed
from .wiki_commit import commit
from .wiki_reuse import prepare as reuse_pages
from .wiki_compile import stack


@timed('wiki.build', scope='corpus')
def build(db, root, sources, pages, runs=None, snapshot=None):
    runs = accepted_runs(db) if runs is None else runs
    with span(db, 'wiki.page_render', scope='corpus', publications=len(sources), pages=len(pages)) as timing:
        files = render(sources, pages)
        timing.update(files=len(files), bytes=sum(len(body) for body in files.values()))
    render_policy = {'renderer': 2, 'implementation': policy('wiki-render'), 'mkdocs': '1.6.1', 'compiler':stack(), 'sources': digest(sources), 'mappings': digest(pages), 'mapping_runs': runs}
    identity = digest({'policy': render_policy, 'files': {name: sha256(body) for name, body in files.items()}})
    previous = cached(db, root, identity)
    if previous is not None:
        manifest = json.loads(previous[0])
        with span(db, 'wiki.render_reuse', reused_files=len(files)) as reuse:
            reuse['skipped_stages'] = ['wiki.site_render', 'wiki.link_validation', 'wiki.file_validation']
        with span(db, 'wiki.commit', generation=identity, scope='corpus'):
            commit(db, root, identity, manifest, sources, pages, runs, snapshot)
        return manifest
    reuse=reuse_pages(root,render_policy,files)
    prefix = 'wiki/builds/' + identity
    with span(db, 'wiki.file_write', files=len(files), scope='corpus'):
        write_markdown(db,root,prefix,files)
    with span(db, 'wiki.site_render', scope='corpus', pages=len(pages)) as timing:
        render_site(root,prefix,reuse)
        timing.update(files=len(files),reused_html=reuse.get('compiled_reused',0) if reuse else 0)
    with span(db, 'wiki.file_validation', scope='corpus') as timing:
        manifest = file_manifest(root, prefix, identity, render_policy, sources)
        timing.update(files=len(manifest['files']), bytes=sum(
            (root / name).stat().st_size for name in manifest['files']))
    with span(db, 'wiki.commit', generation=identity, scope='corpus'):
        commit(db, root, identity, manifest, sources, pages, runs, snapshot)
    return manifest
