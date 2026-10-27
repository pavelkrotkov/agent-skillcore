import json

from x_publication_fixtures import PublicationCase
from x_curator.executions import verified_execution
from x_curator.model_trace import pack
from x_curator.publication import publish
from x_curator.receipts import encoded
from x_curator.storage import sha256
from x_curator.worker_prompts import prompt
from x_trace_fixtures import rollout


def traced(row):
    request, packet = json.loads(row['input']), json.loads(row['output'])
    text = prompt(request)
    rows = [{'type': 'session_meta', 'payload': {'id': row['session']}},
            {'type': 'response_item', 'payload': {'type': 'message', 'role': 'user',
                'content': [{'type': 'input_text', 'text': text}]}},
            {'type': 'response_item', 'payload': {'type': 'message', 'role': 'assistant', 'phase': 'final_answer',
                'content': [{'type': 'output_text', 'text': encoded(packet).decode()}]}}]
    return pack(request, text, ['synthetic'], row['log'], rollout(rows))


class TracePublicationTests(PublicationCase):
    def test_publication_rechecks_input_binding_even_when_log_checksum_is_updated(self):
        proposal, review = self.approved_executions()
        for identity in (proposal, review):
            row = self.db.execute('SELECT * FROM executions WHERE id=?', (identity,)).fetchone()
            log = traced(row)
            with self.db:
                self.db.execute('UPDATE executions SET log=?,log_sha=? WHERE id=?', (log, sha256(log), identity))
        publish(self.db, self.root, self.token, proposal, review)
        row = self.db.execute('SELECT * FROM executions WHERE id=?', (proposal,)).fetchone()
        proof = json.loads(row['log'])
        proof['request_sha'] = 'changed'
        changed = encoded(proof)
        with self.db:
            self.db.execute('UPDATE executions SET log=?,log_sha=? WHERE id=?', (changed, sha256(changed), proposal))
        with self.assertRaisesRegex(ValueError, 'controller request'):
            verified_execution(self.db, proposal, 'research', self.token)
