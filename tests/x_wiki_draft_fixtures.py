from copy import deepcopy
import json
import os
import subprocess
import sys

from x_wiki_fixtures import WikiCase, events
from x_fixtures import SCRIPTS
from x_curator.wiki_build import build


class WikiDraftCase(WikiCase):
    corrected = True

    def setUp(self):
        super().setUp()
        build(self.db, self.root, self.sources, {})
        self.previous = (self.root / 'wiki/CURRENT.json').read_bytes()

    def draft_model(self, request):
        if request['role'] != 'organize':
            return self.model(request)
        row = dict(self.db.execute('SELECT * FROM wiki_runs').fetchone())
        before = '\n'.join(self.db.iterdump())
        bad = deepcopy(self.mapping)
        page = bad['pages'][0]
        link = dict(kind=page['kind'], title=page['title'], reason='Synthetic relationship', claims=page['claims'])
        page['related'] = [link]
        self_link = deepcopy(bad)
        link['title'] = 'Missing target'
        messages = [dict(id=1, method='tools/list'),
                    dict(id=10, method='tools/call', params={'name': 'context', 'arguments': {}})]
        messages += [dict(id=n, method='tools/call', params={'name': 'validate', 'arguments': {'proposal': value}})
                     for n, value in enumerate((self_link, bad, self.mapping), 2)]
        response = subprocess.run([sys.executable, '-m', 'x_curator.wiki_mcp', str(self.root), row['id']],
                                  input='\n'.join(map(json.dumps, messages)) + '\n', env=dict(os.environ, PYTHONPATH=str(SCRIPTS)),
                                  capture_output=True, text=True, check=True, timeout=10)
        results = [json.loads(line)['result'] for line in response.stdout.splitlines()]
        self.assertEqual([t['name'] for t in results[0]['tools']], ['validate', 'context'])
        self.assertEqual(results[1]['structuredContent']['input_sha'], row['input_sha'])
        self.assertEqual([r['isError'] for r in results[2:]], [True, True, False])
        self.assertIn('self-referential', results[2]['content'][0]['text'])
        self.assertIn('missing-target', results[3]['content'][0]['text'])
        self.assertEqual('\n'.join(self.db.iterdump()), before)
        self.assertEqual((self.root / 'wiki/CURRENT.json').read_bytes(), self.previous)
        return events(self.mapping if self.corrected else bad)
