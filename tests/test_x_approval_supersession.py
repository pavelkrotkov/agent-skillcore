from x_supersession_fixtures import SupersessionCase
from x_curator import deep_claim, deep_permission


class ApprovalSupersessionTests(SupersessionCase):
    def test_fresh_mixed_approval_preserves_old_rows_and_revokes_old_execution(self):
        self.prepare(2)
        self.observe()
        self.reply('research ' + self.references[0])
        old = dict(self.permission(self.value['id'], self.references[0]))
        decision = tuple(self.db.execute('SELECT * FROM review_decisions').fetchone())
        self.new_scope()
        clauses = 'research ' + ','.join(self.references)
        self.reply(clauses, identity='fresh-human')
        self.reply(clauses, identity='fresh-human')
        self.assertEqual(dict(self.permission(old['delivery'], old['reference'])), old)
        self.assertEqual(tuple(self.db.execute('SELECT * FROM review_decisions WHERE delivery=?', (old['delivery'],)).fetchone()), decision)
        self.assertEqual(self.db.execute('SELECT count(*) FROM research_permissions').fetchone()[0], 3)
        with self.assertRaisesRegex(ValueError, 'superseded'):
            deep_claim.claim(self.db, old['id'])
        current = self.permission(self.value['id'], self.references[0])
        self.assertIsNotNone(deep_claim.claim(self.db, current['id']))
        self.assertEqual(self.db.execute('SELECT count(*) FROM deep_runs').fetchone()[0], 1)

    def test_failed_mixed_reply_cannot_supersede_existing_authorization(self):
        self.prepare(2)
        self.observe()
        self.reply('research ' + self.references[0])
        old = dict(self.permission(self.value['id'], self.references[0]))
        self.new_scope()
        source = self.references[1].split(':')[-1]
        with self.db:
            self.db.execute("UPDATE jobs SET state='excluded' WHERE id=?", (source,))
        with self.assertRaises(ValueError):
            self.reply('research ' + ','.join(self.references), identity='invalid-fresh-human')
        self.assertEqual(self.db.execute('SELECT count(*) FROM research_supersessions').fetchone()[0], 0)
        self.assertEqual(self.db.execute('SELECT count(*) FROM research_permissions').fetchone()[0], 1)
        self.assertEqual(deep_permission.verified(self.db, old['id'])[0]['id'], old['id'])

    def test_consumed_historical_permission_remains_verifiable(self):
        self.authorize()
        self.deep()
        old = dict(self.db.execute('SELECT * FROM research_permissions').fetchone())
        self.new_scope()
        self.reply('research ' + self.references[0], identity='later-human')
        self.assertEqual(deep_permission.verified(self.db, old['id'])[0], old)
        self.assertEqual(self.db.execute('SELECT count(*) FROM research_supersessions').fetchone()[0], 0)
