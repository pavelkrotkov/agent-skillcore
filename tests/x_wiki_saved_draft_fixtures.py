from copy import deepcopy
import json

from x_wiki_final_fixtures import WikiFinalCase, compact
from x_wiki_fixtures import WikiCase
from x_curator import wiki_saved_draft
from x_curator.receipts import digest, encoded
from x_curator.wiki_notes import request


def reference_log(request, packet, arguments):
    value = json.loads(compact(request, packet))
    events = [json.loads(line) for line in value['events'].splitlines()]
    events[1]['item']['arguments'] = arguments
    value['events'] = '\n'.join(encoded(event).decode() for event in events)
    return encoded(value)



class SavedDraftProofCase(WikiFinalCase):
    def setUp(self):
        super().setUp()
        page = self.proposal['pages'][0]
        other = deepcopy(page)
        other['title'] = 'Synthetic comparison'
        page['related'] = [dict(kind='concept', title=other['title'], reason='Synthetic comparison.', claims=page['claims'])]
        self.inputs['saved_draft'] = dict(format=wiki_saved_draft.VERSION, pages=[page, other])
        self.inputs['saved_draft_sha'] = digest(self.inputs['saved_draft'])
        self.args = dict(input_sha=digest(self.inputs), saved_draft_sha=self.inputs['saved_draft_sha'])
        self.proposal = wiki_saved_draft.proposal(self.args, self.inputs)
        self.request = request('organize', self.inputs)



class SavedDraftStoreCase(WikiCase):
    def save(self, pages=None):
        path = self.root / 'recovery.json'
        path.write_text(json.dumps(dict(pages=self.mapping['pages'] if pages is None else pages)))
        return path


def broken_log(request, packet, arguments, mode):
    value = json.loads(reference_log(request, packet, arguments))
    events = [json.loads(line) for line in value['events'].splitlines()]
    if mode == 'incomplete': events.pop()
    if mode == 'missing': events.pop(1)
    if mode == 'foreign': events[1]['item']['server'] = 'other'
    if mode == 'failed': events[1]['item']['status'] = 'failed'
    value['events'] = '\n'.join(encoded(event).decode() for event in events)
    return encoded(value)
