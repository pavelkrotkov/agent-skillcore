"""Concurrent first-use and legacy migrations must share a writer reservation."""
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from threading import Barrier

from x_fixtures import CollectionCase
from x_curator import provider_health


class MigrationConnection(sqlite3.Connection):
    def execute(self, sql, parameters=()):
        if sql.startswith('ALTER TABLE provider_health ADD COLUMN generation') and not self.in_transaction:
            self.migration_gate.wait(timeout=5)
        return super().execute(sql, parameters)


class ProviderInitializationTests(CollectionCase):
    def initialize_together(self):
        gate = Barrier(2)
        def initialize(_):
            with closing(sqlite3.connect(self.root / 'curator.sqlite3', timeout=5, factory=MigrationConnection)) as db:
                db.row_factory = sqlite3.Row
                db.migration_gate = gate
                provider_health.initialize(db)
                return {row['name'] for row in db.execute('PRAGMA table_info(provider_health)')}
        with ThreadPoolExecutor(max_workers=2) as workers:
            columns = list(workers.map(initialize, range(2)))
        self.assertEqual(columns, [{'route', 'retry_at', 'action', 'generation', 'failed_at'}] * 2)

    def test_first_use_initializers_do_not_race_the_same_column_migration(self):
        self.initialize_together()

    def test_legacy_initializers_preserve_the_existing_provider_cooldown(self):
        self.db.execute('CREATE TABLE provider_health(route TEXT PRIMARY KEY,retry_at REAL NOT NULL,action TEXT NOT NULL)')
        with self.db:
            self.db.execute("INSERT INTO provider_health VALUES ('legacy',9999,'retained cooldown')")
        self.initialize_together()
        self.assertEqual(tuple(self.db.execute("SELECT route,retry_at,action FROM provider_health").fetchone()),
                         ('legacy', 9999, 'retained cooldown'))
