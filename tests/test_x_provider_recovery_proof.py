import json
from unittest.mock import patch

from x_publication_fixtures import PublicationCase, events
from x_provider_fixtures import recovery_proof
from x_curator import provider_health as health
from x_curator.codex_profile import command
from x_curator.provider_recovery import recover
from x_curator.receipts import encoded


class ProviderRecoveryProofTests(PublicationCase):
    def test_old_foreign_incomplete_and_tampered_proofs_preserve_cooldown(self):
        with patch('time.time', return_value=100):
            health.suspend(self.db, 'failure')
        failure = health.current(self.db)
        request = {'role': 'research', 'bundle': self.evidence, 'proposal': None}
        args = command('codex', False) + ['-']
        receipt = json.loads(recovery_proof(request, 102))
        variants = [dict(receipt, profile=['other-model']), dict(receipt, request_sha='changed'),
                    dict(receipt, events=events({}).decode().rsplit('\n', 1)[0])]
        logs = [encoded(v) for v in variants] + [events({}), recovery_proof(request, 99)]
        for log in logs:
            with self.subTest(log_size=len(log)), self.assertRaises(ValueError):
                recover(self.db, failure, 101, request, log, args)
            self.assertEqual(health.current(self.db), failure)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM provider_recoveries').fetchone()[0], 0)
