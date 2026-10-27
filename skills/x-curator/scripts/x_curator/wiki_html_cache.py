"""Reuse authenticated HTML parsing facts by bytes; validate every target afresh."""
from marshal import dumps,loads
from . import audit_memo
from .html_text import Links
from .storage import sha256
from .proof_mode import FULL

IDENTITY=('wiki-links',0)


def documents(site,root):
    record=audit_memo.read(root,IDENTITY) if root is not None and not FULL.get() else None
    previous=loads(record[0]) if record else {}
    result,facts={},{}
    for path in site.rglob('*.html'):
        body=path.read_bytes()
        identity=sha256(body)
        parser=Links()
        if identity in previous:
            parser.urls,parser.ids=previous[identity]
        else:
            parser.feed(body.decode())
        result[path]=parser
        facts[identity]=parser.urls,parser.ids
    return result,facts


def save(root,facts):
    if root is not None:
        audit_memo.retain(root,IDENTITY,(dumps(facts),{},{},({},{}),{}))
