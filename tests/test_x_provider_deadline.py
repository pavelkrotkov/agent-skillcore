from unittest.mock import patch

from x_publication_fixtures import PublicationCase
from x_curator.codex_profile import login_status
from x_curator.codex_runner import run
from x_curator.deadlines import DeadlineExceeded
from x_curator.worker_process import process
from x_curator import provider_health


class ProviderDeadlineTests(PublicationCase):
    def test_controller_expiry_does_not_open_provider_circuit(self):
        with patch('x_curator.codex_profile.subprocess.run', side_effect=DeadlineExceeded('phase limit')):
            with self.assertRaises(DeadlineExceeded):
                login_status('codex', {})
        request = {'role': 'research', 'bundle': self.evidence, 'proposal': None}
        variants = [(request, 900), (dict(request, role='discover'), 300), (dict(request, role='review'), 300),
                    (dict(request, role='organize', bundle={'captures': {}, 'wiki_inputs': {}}), 900),
                    (dict(request, role='organize_review', bundle={'captures': {}, 'wiki_inputs': {}}), 600),
                    (dict(request, reading={'stage': 'composition'}), 600),
                    (dict(request, reading={'stage': 'segment'}), 900),
                    (dict(request, role='review', reading={'stage': 'segment'}), 600)]
        for variant, seconds in variants:
            with patch('x_curator.process_group.subprocess.run', side_effect=DeadlineExceeded('phase limit')) as execute:
                with self.assertRaises(DeadlineExceeded):
                    run(self.db, self.root, 'codex', {}, variant)
                self.assertEqual(execute.call_args.kwargs['timeout'], seconds)
        job = dict(self.db.execute('SELECT * FROM jobs').fetchone())
        with patch('x_curator.worker_process.research', side_effect=DeadlineExceeded('phase limit')):
            self.assertEqual(process(self.db, self.root, None, job)['state'], 'retry')
        self.assertIsNone(provider_health.blocked(self.db))
