import json
import time
from unittest.mock import patch

from x_native_search_fixtures import NativeCase
from x_quick_fixtures import native
from x_quick_phase_final import finish
from x_curator import quick_mcp, quick_process
from x_curator.receipts import digest


class PhaseCase(NativeCase):
    final = finish

    def setUp(self):
        super().setUp()
        self.started = self.at = time.time()
        self.final_calls = 0
        self.cutoff_change = lambda receipt: receipt

    def acquisition(self, request):
        self.initial = request
        root = self.root / 'runs' / self.token
        root.mkdir(parents=True, exist_ok=True)
        (root / (digest(request) + '.jsonl')).write_bytes(self.search_log)
        self.at = self.started + 60
        self.read = quick_mcp.call(self.db, self.token, 'read', {'source': 'https://example.test/release'})
        self.decision = self.packet_for(json.loads(self.read['content'][0]['text'])['capture'])
        proof = json.loads(native(request, {'notes': 'Untrusted draft'}, [self.read], self.search_log))
        proof['events'] = '\n'.join(proof['events'].split('\n')[:-2]) + '\n'
        proof['rollout'] = '\n'.join(proof['rollout'].split('\n')[:-1])
        self.at = self.started + 80
        return self.cutoff_change(dict(status='cutoff', stopped=self.at, ended=self.at, input_proof=proof))

    def run_phases(self, final=None):
        def executor(request):
            return (final or self.final)(request)
        executor.evidence = self.acquisition
        with patch('time.time', side_effect=lambda: self.at), patch('x_curator.quick_web.fetch', self.fetch), \
                patch('x_curator.quick_process.runner', return_value=executor):
            return quick_process.research(self.db, self.root, self.client, self.token)
