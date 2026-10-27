from x_publication_fixtures import PublicationCase
from x_curator.executions import verified_execution
from x_curator.receipts import digest, encoded


class ExecutionDiagnosticsTests(PublicationCase):
    def test_hash_and_session_failures_name_the_exact_checked_component(self):
        identity, _ = self.approved_executions()
        for column in ('input_sha', 'output_sha', 'log_sha', 'session'):
            original = self.db.execute('SELECT ' + column + ' FROM executions WHERE id=?', (identity,)).fetchone()[0]
            with self.db:
                self.db.execute('UPDATE executions SET ' + column + '=? WHERE id=?', ('different', identity))
            with self.assertRaisesRegex(ValueError, 'tampered execution receipt: ' + column):
                verified_execution(self.db, identity, 'research', self.token)
            with self.db:
                self.db.execute('UPDATE executions SET ' + column + '=? WHERE id=?', (original, identity))

    def test_answer_and_semantic_role_fail_closed_without_logging_packet_content(self):
        identity, _ = self.approved_executions()
        with self.assertRaisesRegex(ValueError, 'semantic_role'):
            verified_execution(self.db, identity, 'research', self.token, semantic_role='review')
        changed = {'private-payload-must-not-appear': True}
        with self.db:
            self.db.execute('UPDATE executions SET output=?,output_sha=? WHERE id=?',
                            (encoded(changed).decode(), digest(changed), identity))
        with self.assertRaisesRegex(ValueError, 'answer') as caught:
            verified_execution(self.db, identity, 'research', self.token)
        self.assertNotIn('private-payload', str(caught.exception))
