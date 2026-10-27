"""Use the established MkDocs compiler for the private wiki."""
import subprocess

from .publication_files import write_verified, private_target
from .receipts import encoded
from .storage import sha256


def render_site(root,prefix,reuse=None):
    from . import wiki_compile
    folder = safe_tree(root, prefix)
    config={'site_name':'Knowledge wiki','docs_dir':'docs','site_dir':'site','nav':wiki_compile.NAV,
            'use_directory_urls':False,'theme':{'name':'mkdocs','highlightjs':False},
            'validation':{'links':{'not_found':'warn','anchors':'warn'}}}
    write_verified(root, prefix + '/mkdocs.yml', encoded(config))
    try:
        wiki_compile.invoke(folder/'mkdocs.yml',reuse)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        stderr = exc.stderr or b'No compiler stderr received.'
        write_verified(root, prefix + '/diagnostics/' + sha256(stderr) + '.txt', stderr)
        raise
    safe_tree(root, prefix)
    return folder / 'site'



def safe_tree(root, prefix):
    folder = private_target(root, prefix)
    for path in [folder, *folder.parents, *folder.rglob('*')]:
        if path.is_symlink() or path.name == '.git':
            raise ValueError('wiki build tree contains a symlink or Git checkout')
    return folder
