from x_publication_fixtures import PublicationCase, events
from x_curator.publication import publish
from x_curator.receipts import digest
from x_curator import wiki_inputs, wiki_store
from x_curator.wiki_catalog import prepare
from unittest.mock import patch
from x_trace_fixtures import proof
from x_curator.wiki_mapping import map_sources


class WikiCase(PublicationCase):
    def setUp(self):
        super().setUp()
        proposal, review = self.approved_executions()
        self.publication = publish(self.db, self.root, self.token, proposal, review)
        wiki_store.initialize(self.db)
        self.sources = wiki_inputs.sources(self.db, self.root)
        self.inputs = prepare(self.sources, {}, [self.publication])
        self.mapping = {'input_sha': digest(self.inputs), 'pages': [{
            'kind': 'concept', 'title': 'Synthetic evidence', 'description': 'Evidence in synthetic demonstrations.',
            'claims': [{'publication': self.publication, 'claim': 'c1'}], 'related': [],
            'synthesis': [{'text': 'Synthetic demonstrations illustrate evidence checks.',
                           'claims': [{'publication': self.publication, 'claim': 'c1'}]}]}]}

    def model(self, request):
        if request['role'] == 'organize':
            return events(self.mapping)
        return events({'verdict': 'approve', 'input_sha': digest(self.inputs),
                       'proposal_sha': digest(self.mapping), 'findings': []})

    def feedback_response(self, request, findings=None, session=None):
        inputs = request['bundle']['wiki_inputs']
        packet = dict(self.mapping, input_sha=digest(inputs))
        if request['role'] == 'organize':
            return proof(request, packet, session=session)
        verdict = dict(verdict='reject' if findings else 'approve', input_sha=digest(inputs),
                       proposal_sha=digest(packet), findings=findings or [])
        return proof(request, verdict, session=session)

    def reject_mapping(self, finding='The page title implies an unsupported relationship.'):
        with patch('x_curator.wiki_mapping.runner', return_value=lambda r: self.feedback_response(r, [finding])):
            with self.assertRaisesRegex(ValueError, 'independent approval'):
                map_sources(self.db, self.inputs)
        return dict(self.db.execute('SELECT * FROM wiki_runs ORDER BY started DESC LIMIT 1').fetchone())
