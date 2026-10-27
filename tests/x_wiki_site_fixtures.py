from unittest.mock import patch
from x_curator.publication_files import write_verified
from x_curator.wiki_site import render_site
from x_curator.wiki_files import file_manifest


def compile_files(root,identity,files,reuse=None):
    prefix='wiki/builds/'+identity
    for name,text in files.items():
        write_verified(root,prefix+'/docs/'+name,text.encode())
    with patch.dict('os.environ',{'PYTHONPATH':''}):
        render_site(root,prefix,reuse)
    return file_manifest(root,prefix,identity,{}, {})
