import json
from unittest.mock import patch

from x_publication_fixtures import PublicationCase
from x_trace_fixtures import proof
from x_curator import blobs, reading_work
from x_curator.evidence import save_capture
from x_curator.receipts import digest, encoded



class ReadingCase(PublicationCase):
    def setUp(self):
        super().setUp()
        self.addCleanup(patch.stopall)
        patch('x_curator.reading_plan.CURRENT_VERSION', 1).start()
        patch.dict('x_curator.reading_plan.POLICIES', {1: {'width': 400, 'context': 20, 'max_segments': 8}}).start()
        body = ('α Original interval evidence.\n' * 35).encode()
        self.book = save_capture(self.db, self.token, {'kind': 'text', 'url': 'https://example.test/book',
                                                      'text': body.decode(), 'body_sha': blobs.put(self.db, body)})
        self.calls = []

    def model(self, request):
        self.calls.append(request)
        if request['role'] == 'review':
            output = dict(verdict='approve', proposal_sha=digest(request['proposal']),
                          bundle_sha=request['bundle_sha'], findings=[])
        elif request['reading']['stage'] == 'composition':
            claim = request['bundle']['approved_segment_claims']['claims'][0]['id']
            output = {key: {'text': 'Synthetic source interpretation.', 'claims': [claim]} for key in ('title', 'summary')}
        else:
            output = self.segment(request)
        images = {sha: blobs.read(self.db, sha) for c in request['bundle']['captures'].values() for sha in c.get('images', [])}
        return proof(request, output, images=images)

    def segment(self, request):
        captures = request['bundle']['captures']
        claims = [dict(self.packet['claims'][0], id=f'c{index + 1}', citations=[{'capture': key, 'line_start': 'L000000', 'line_end': 'L000000'}])
                  for index, (key, capture) in enumerate(captures.items())]
        return dict(claims=claims, limitations=[], empty_reason='',
                    coverage=[dict(capture=key, status='covered', notes='Entire primary interval reviewed.') for key in captures])

    def publish_reading(self):
        return reading_work.run(self.db, self.root, self.token, self.model)

    def replace_receipt(self, identity, request, output, session=None):
        from x_curator.storage import sha256
        log = proof(request, output, session)
        from x_curator.model_events import result
        session, _ = result(log)
        with self.db:
            self.db.execute('UPDATE executions SET input=?,input_sha=?,output=?,output_sha=?,log=?,log_sha=?,session=? WHERE id=?',
                            (encoded(request).decode(), digest(request), encoded(output).decode(), digest(output), log, sha256(log), session, identity))

    def receipt(self, role):
        row = self.db.execute('SELECT * FROM executions WHERE role=?', (role,)).fetchone()
        return row, json.loads(row['input']), json.loads(row['output'])
