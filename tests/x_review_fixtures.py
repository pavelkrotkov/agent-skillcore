from x_batch_fixtures import BatchCase
from x_curator import batch_report, review_decisions, review_outbox, review_receipts


def readback(chat, identity, text, kind='agentMessage'):
    item = {'id': identity, 'type': kind, 'text': text}
    if kind == 'userMessage':
        item = {'id': identity, 'type': kind, 'content': [{'type': 'text', 'text': text}]}
    return {'schemaVersion': 1, 'thread': {'id': chat, 'kind': 'codex'},
            'turns': [{'id': 'synthetic-turn', 'startedAt': 1, 'items': [item]}]}


class ReviewCase(BatchCase):
    def prepare(self, count=1):
        self.add_items(count)
        self.checker = self.pending
        self.run_batch()
        batch = batch_report.report(self.db)['batches'][0]
        self.value = review_outbox.prepare(self.db, batch['id'], 'synthetic-chat')
        self.references = [item['reference'] for item in batch['review']]
        return self.value

    def observe(self):
        value = self.value
        receipt = readback(value['chat'], 'synthetic-delivery', value['message'])
        return review_receipts.observe(self.db, value['id'], receipt, 'synthetic-delivery')

    def reply(self, clauses, identity='synthetic-human', **kwargs):
        value = self.value
        text = 'review ' + value['id'] + '; ' + clauses
        receipt = readback(value['chat'], identity, text, 'userMessage')
        return review_decisions.apply(self.db, value['id'], receipt, identity,
                                      human_origin_confirmed=True, **kwargs)
