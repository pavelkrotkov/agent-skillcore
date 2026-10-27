"""Native structured output bounds the final answer; the full draft stays in receipts."""
import json
from .quick_final import FORMAT
from .receipts import digest


def configure(args, root, request):
    if request.get('final_format') != FORMAT:
        return
    value = {'type': 'object', 'properties': {'format': {'type': 'string', 'enum': [FORMAT]},
             'decision_sha': {'type': 'string', 'pattern': '^[0-9a-f]{64}$'}},
             'required': ['format', 'decision_sha'], 'additionalProperties': False}
    path = root / (digest(request)+'.schema.json')
    root.mkdir(parents=True, mode=0o700, exist_ok=True)
    path.write_text(json.dumps(value))
    args.extend(['--output-schema', str(path)])
