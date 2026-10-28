"""Load only an explicitly selected private pages-only draft before reservation."""
import json
from pathlib import Path

from .receipts import digest
from .wiki_contract import validate
from .wiki_prompts import preflight
from .wiki_saved_draft import VERSION, proposal


def attach(inputs, filename, root):
    if filename is None:
        return
    path = Path(filename).resolve()
    if not path.is_relative_to(Path(root).resolve()):
        raise ValueError('saved draft must be inside the private state folder')
    raw = path.read_bytes()
    draft = json.loads(raw)
    if not isinstance(draft, dict) or set(draft) != {'pages'} or not isinstance(draft['pages'], list):
        raise ValueError('saved draft must contain only pages')
    inputs['saved_draft'] = dict(format=VERSION, pages=draft['pages'])
    inputs['saved_draft_sha'] = digest(inputs['saved_draft'])
    validate(proposal(dict(input_sha=digest(inputs), saved_draft_sha=inputs['saved_draft_sha']), inputs), inputs)
    preflight(inputs)
