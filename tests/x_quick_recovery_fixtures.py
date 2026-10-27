import json
import time

from x_review_fixtures import ReviewCase


class RecoveryCase(ReviewCase):
    def affected(self):
        self.prepare()
        self.observe()
        check = dict(self.db.execute('SELECT * FROM quick_checks').fetchone())
        error = json.dumps({'isError': True, 'content': [{'type': 'text', 'text': 'substring not found'}]})
        with self.db:
            self.db.execute('INSERT INTO quick_tools VALUES(?,?,?,?,?,?,?)',
                            ('historical-bug', check['token'], 'read', '{}', error, time.time(), time.time()))
        return check
