import json

from x_review_fixtures import ReviewCase
from x_curator import deep_permission


class ReviewKeyNoteTests(ReviewCase):
    def test_key_status_note_preserves_native_message_and_permission_replay(self):
        self.prepare()
        self.observe()
        text = 'research ' + self.references[0] + '\nadded command code key'
        self.reply(text)
        permission = self.db.execute('SELECT id FROM research_permissions').fetchone()[0]
        actual, proposal = deep_permission.verified(self.db, permission)
        self.assertEqual(actual['seconds'], proposal['seconds'])
        self.assertIsNone(actual['consumed'])
        message = json.loads(self.db.execute('SELECT receipt FROM review_replies').fetchone()[0])
        self.assertTrue(message['content'][0]['text'].endswith(text))
        self.reply(text)
        self.assertEqual(self.db.execute('SELECT count(*) FROM research_permissions').fetchone()[0], 1)

    def test_unknown_or_conflicting_followup_does_not_create_permission(self):
        self.prepare()
        self.observe()
        for suffix in ('exclude 10', 'do not run', 'added command code key; research 99'):
            with self.subTest(suffix=suffix), self.assertRaises(ValueError):
                self.reply('research ' + self.references[0] + '\n' + suffix)
        self.assertEqual(self.db.execute('SELECT count(*) FROM research_permissions').fetchone()[0], 0)
