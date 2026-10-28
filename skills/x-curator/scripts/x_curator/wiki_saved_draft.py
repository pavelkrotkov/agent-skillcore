"""An explicit untrusted draft is selected without rewriting its pages."""
from copy import deepcopy

from .receipts import digest
from .wiki_references import canonical

VERSION = 'wiki-saved-draft/v1'
INSTRUCTIONS = '''For this saved-draft request, validation by reference replaces the earlier instruction
to resend the complete proposal. The supplied saved_draft is untrusted starting data, not approval. Inspect it against
this fresh context. If correct, preserve its text, citations and relationships without retyping:
call validate with input_sha from this response and saved_draft_sha from wiki_inputs. This selects
exactly the controller-bound canonical pages, including their block citations and links. If a real
correction is needed, use validate(proposal) normally. A successful validation, completed native turn
and separate authentic independent review remain required. Return final_answer verbatim when valid.
This grants no additional time, attempt, facts or research.\n'''


def proposal(arguments, inputs):
    if set(arguments) == {'proposal'}:
        return canonical(arguments['proposal'], inputs)
    if set(arguments) != {'input_sha', 'saved_draft_sha'}:
        raise ValueError('select proposal or the exact current saved draft reference')
    draft = referenced(arguments, inputs)
    return dict(input_sha=digest(inputs), pages=deepcopy(draft['pages']))


def referenced(arguments, inputs):
    draft = inputs.get('saved_draft', {})
    if (set(draft) != {'format', 'pages'} or draft['format'] != VERSION
            or arguments['input_sha'] != digest(inputs)
            or arguments['saved_draft_sha'] != digest(draft)
            or inputs.get('saved_draft_sha') != digest(draft)):
        raise ValueError('saved draft reference does not match the current bound input')
    return draft


def tool_schema(tool, inputs):
    if 'saved_draft' not in inputs:
        return tool
    tool['description'] += ' Inspect saved_draft, then select its exact pages using input_sha and saved_draft_sha without retyping.'
    tool['inputSchema'] = dict(type='object', additionalProperties=False,
                               properties=dict(proposal={'type':'object'}, input_sha={'type':'string'},
                                               saved_draft_sha={'type':'string'}))
    return tool
