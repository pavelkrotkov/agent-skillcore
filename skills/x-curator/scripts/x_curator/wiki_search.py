"""Reuse authenticated HTML bytes and preserve only their matching search entries."""
import json
from urllib.parse import urlsplit
from .storage import sha256
from .proof_files import read


def retained(plan,relative,namespace):
    path='wiki/builds/'+plan['manifest']['generation']+'/site/'+relative
    body,_=read((plan['root'],path),namespace)
    if sha256(body)!=plan['manifest']['files'][path]:
        raise ValueError('inherited wiki artifact changed')
    return body


def merge(plan,path,namespace):
    previous=json.loads(retained(plan,'search/search_index.json',namespace))
    current=json.loads(path.read_bytes())
    html={name[:-3]+'.html' for name in plan['docs']}
    entries={row['location']:row for row in previous['docs'] if urlsplit(row['location']).path in html}
    entries.update((row['location'],row) for row in current['docs'])
    current['docs']=[entries[key] for key in sorted(entries)]
    path.write_text(json.dumps(current,ensure_ascii=False,separators=(',',':')))
