from x_publication_fixtures import PublicationCase
from x_curator import policy_migration
from x_curator.publication import publish
from x_fixtures import Client, CollectionCase, collect, envelope, tweet_entry


class PublicationMigrationTests(PublicationCase):
    def test_valid_legacy_fresh_publication_needs_no_new_research(self):
        proposal, review = self.approved_executions()
        identity = publish(self.db, self.root, self.token, proposal, review)
        plan = policy_migration.preview(self.root)
        self.assertEqual(plan['counts'], {'valid_publication': 1})
        self.assertEqual(plan['items'][0]['publications'][0]['id'], identity)
        policy_migration.apply(self.root, plan['digest'])
        self.assertEqual(self.db.execute('SELECT count(*) FROM policy_transitions').fetchone()[0], 0)
        self.assertEqual(self.db.execute('SELECT count(*) FROM executions').fetchone()[0], 2)


class CollectionMigrationTests(CollectionCase):
    def test_collected_only_database_needs_no_live_schema_changes_for_preview(self):
        collect(self.db, Client([(200, envelope([{'type': 'TimelineAddEntries', 'entries': [tweet_entry('1')]}]))]), 'likes', delay=0)
        before = list(self.db.iterdump())
        plan = policy_migration.preview(self.root)
        self.assertEqual(plan['counts'], {'quick_check': 1})
        self.assertEqual(list(self.db.iterdump()), before)
        policy_migration.apply(self.root, plan['digest'])
        self.assertEqual(self.db.execute('SELECT state FROM jobs').fetchone()[0], 'pending')
