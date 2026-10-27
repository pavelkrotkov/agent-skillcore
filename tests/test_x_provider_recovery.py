import sqlite3
from unittest.mock import patch

from x_publication_fixtures import PublicationCase
from x_provider_fixtures import recovery_proof
from x_curator import provider_health as health
from x_curator.codex_profile import command
from x_curator.provider_recovery import recover


class ProviderRecoveryTests(PublicationCase):
    def test_legacy_migration_and_exact_generation_atomic_recovery(self):
        self.db.execute('CREATE TABLE provider_health(route TEXT PRIMARY KEY,retry_at REAL NOT NULL,action TEXT NOT NULL)')
        with self.db:
            self.db.execute('INSERT INTO provider_health VALUES (?,?,?)', (health.ROUTE, 9999, 'legacy'))
        legacy = health.current(self.db)
        self.assertEqual((legacy['retry_at'], legacy['generation']), (9999, None))
        self.assertFalse(recover(self.db, legacy, 1, {}, b'', []))
        with patch('time.time', return_value=100):
            health.suspend(self.db, 'new failure')
            first = health.current(self.db)
            health.suspend(self.db, 'same timestamp failure')
        second = health.current(self.db)
        self.assertNotEqual(first['generation'], second['generation'])
        request = {'role': 'research', 'bundle': self.evidence, 'proposal': None}
        log = recovery_proof(request, 102)
        args = (101, request, log, command('codex', False) + ['-'])
        self.assertFalse(recover(self.db, first, *args))
        self.assertEqual(health.current(self.db), second)
        self.db.execute("CREATE TRIGGER fail_journal BEFORE INSERT ON provider_recoveries BEGIN SELECT RAISE(ABORT,'synthetic storage failure'); END")
        with self.assertRaises(sqlite3.IntegrityError):
            recover(self.db, second, *args)
        self.assertEqual(health.current(self.db), second)
        self.db.execute('DROP TRIGGER fail_journal')
        self.assertTrue(recover(self.db, second, *args))
        self.assertFalse(recover(self.db, second, *args))
        self.assertIsNone(health.current(self.db))
        self.assertEqual(self.db.execute('SELECT log FROM provider_recoveries').fetchone()[0], log)
        self.assertEqual(self.db.execute('SELECT attempts,max_attempts FROM jobs').fetchone()[:], (1, 3))
        with self.db:
            self.db.execute('INSERT OR REPLACE INTO provider_health(route,retry_at,action) VALUES (?,?,?)', (health.ROUTE, 9999, 'compatible rollback'))
        self.assertIsNone(health.current(self.db)['generation'])
