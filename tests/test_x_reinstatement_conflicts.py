from x_publication_fixtures import PublicationCase
from x_curator.publication import publish
from x_curator.publication_audit import invalidate
from x_curator.publication_recovery import complete


class ReinstatementConflictTests(PublicationCase):
    def setUp(self):
        super().setUp()
        self.identity = publish(self.db, self.root, self.token, *self.approved_executions())
        self.row = dict(self.db.execute('SELECT * FROM publications').fetchone())
        invalidate(self.db, self.row, 'synthetic verifier defect')

    def test_tampered_file_or_owner_cannot_reinstate(self):
        target = self.root / self.row['path']
        target.write_bytes(b'tampered')
        with self.assertRaisesRegex(ValueError, 'differs from verified evidence'):
            complete(self.db, self.root, self.identity, 'Corrupted file must fail closed')
        target.write_bytes(self.row['body'])
        with self.db:
            self.db.execute("UPDATE jobs SET token='other-owner',lease_until=1")
        with self.assertRaisesRegex(ValueError, 'still owned'):
            complete(self.db, self.root, self.identity, 'Expired owner still prevents completion')
        self.assertEqual(self.db.execute('SELECT count(*) FROM publication_reinstatements').fetchone()[0], 0)
        self.assertEqual(self.db.execute('SELECT state FROM publications').fetchone()[0], 'invalid')

    def test_competing_publication_prevents_restoring_another_version(self):
        row = dict(self.row, id='competing-publication', path='sources/competing.md', state='published')
        with self.db:
            self.db.execute('INSERT INTO publications('+','.join(row)+') VALUES('+','.join('?' for _ in row)+')', tuple(row.values()))
        with self.assertRaisesRegex(ValueError, 'another published version'):
            complete(self.db, self.root, self.identity, 'Another current version must win')
        self.assertEqual(self.db.execute('SELECT count(*) FROM publication_reinstatements').fetchone()[0], 0)
