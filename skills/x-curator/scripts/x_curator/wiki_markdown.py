"""Link verified unchanged Markdown into new immutable generations, syncing once per folder."""
import json
import os
from .publication_files import write_verified
from .proof_namespace import target as checked_target
from .wiki_write_paths import destination,sync
from .proof_files import read
from .storage import sha256


def previous(db,root):
    for row in db.execute('SELECT id,manifest FROM wiki_builds ORDER BY created DESC,id'):
        if (root/'wiki/builds'/row[0]/'docs').is_dir():
            return json.loads(row[1])
    return dict(generation='',files={})


def write(db,root,prefix,files):
    old=previous(db,root)
    namespace,folders={},set()
    for name,body in files.items():
        relative=prefix+'/docs/'+name
        target=destination(root,relative,namespace,folders)
        prior='wiki/builds/'+old['generation']+'/docs/'+name
        if old['files'].get(prior)==sha256(body):
            if not target.exists():
                os.link(checked_target((root,prior),namespace),target,follow_symlinks=False)
            actual,_=read((root,relative),namespace)
            if actual!=body:
                raise ValueError('inherited wiki Markdown changed')
        else:
            write_verified(root,relative,body)
    for folder in folders:
        sync(folder)
