"""Only signed generations under the identical compiler can supply unchanged HTML."""
from marshal import loads
from . import audit_memo
from .wiki_checkpoint_store import IDENTITY
from .proof_mode import FULL
from .storage import sha256

NAVIGATION=('index.md','sources/index.md')


def prepare(root,policy,files):
    manifest=previous(root)
    if manifest is None:
        return None
    if any(manifest['policy'].get(key)!=policy[key] for key in ('renderer','implementation','mkdocs','compiler')):
        return None
    return dict(root=str(root),manifest=manifest,docs=[name for name,body in files.items() if reusable(name,body,manifest)])


def reusable(name,body,manifest):
    prefix='wiki/builds/'+manifest['generation']
    return (name.endswith('.md') and name not in NAVIGATION
            and manifest['files'].get(prefix+'/docs/'+name)==sha256(body)
            and prefix+'/site/'+name[:-3]+'.html' in manifest['files'])


def previous(root):
    record=None if FULL.get() else audit_memo.read(root,IDENTITY)
    if record is None:
        return None
    manifest=loads(record[0])['manifest']
    if (root/'wiki/builds'/manifest['generation']/'site/index.html').is_file():
        return manifest
    return None
