import json
import time

from x_deep_fixtures import DeepCase
from x_curator import review_outbox, deep_store
from x_curator.receipts import digest


class SupersessionCase(DeepCase):
    def new_scope(self):
        deep_store.initialize(self.db)
        value = json.loads(self.value['payload'])
        value['id'] = digest(['synthetic-new-scope', value['id']])
        value['kind'] = 'research-review'
        for item in value['review']:
            item['scope'] = 'Explicitly changed synthetic scope; same approved allowance.'
            previous = self.db.execute('SELECT d.id FROM deep_runs d JOIN research_permissions p ON p.id=d.id WHERE p.source=? ORDER BY d.started DESC LIMIT 1', (item['source'],)).fetchone()
            if previous:
                item['previous_run'] = previous[0]
        with self.db:
            self.db.execute('INSERT INTO curation_batches VALUES(?,?,?,?,?,?)',
                            (value['id'], value['account'], value['kind'], time.time(), time.time(), 'closed'))
            self.value = review_outbox.save(self.db, value, 'synthetic-chat')
        self.observe()

    def permission(self, delivery, reference):
        return self.db.execute('SELECT * FROM research_permissions WHERE delivery=? AND reference=?', (delivery, reference)).fetchone()
