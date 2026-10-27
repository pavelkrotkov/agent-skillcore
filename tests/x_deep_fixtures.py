from unittest.mock import patch

from x_review_fixtures import ReviewCase
from x_curator import deep_process


class DeepCase(ReviewCase):
    def authorize(self):
        value = self.prepare()
        self.observe()
        self.reply('research ' + self.references[0])
        self.approval = self.db.execute('SELECT id FROM research_permissions').fetchone()[0]
        return value

    def deep(self):
        with patch('x_curator.quick_web.fetch', self.fetch), patch('x_curator.quick_search.fetch', self.fetch), patch('x_curator.deep_process.runner', self.model):
            return deep_process.work(self.db, self.root, self.approval)
