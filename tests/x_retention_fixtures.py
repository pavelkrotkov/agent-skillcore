from x_fixtures import CollectionCase
import json
import os
import time
from x_curator import cycle_store, queue, receipts, wiki_store
from x_curator.storage import sha256


class RetentionCase(CollectionCase):
    def setUp(self):
        super().setUp()
        queue.initialize(self.db)
        receipts.initialize(self.db)
        wiki_store.initialize(self.db)
        cycle_store.initialize(self.db)
        self.now = time.time()

    def build(self, number, current=False):
        identity = f'{number:064x}'
        relative = 'wiki/builds/' + identity + '/site/index.html'
        path = self.root / relative
        path.parent.mkdir(parents=True)
        path.write_bytes(b'valid wiki')
        manifest = dict(generation=identity, files={relative: sha256(path.read_bytes())}, sources=[], policy={})
        self.db.execute('INSERT INTO wiki_builds VALUES (?,?,?)', (identity, json.dumps(manifest), number))
        self.db.commit()
        if current:
            (self.root / 'wiki/CURRENT.json').write_text(json.dumps(dict(generation=identity)))
        return path.parents[1]

    def age(self, path):
        old = self.now - 40 * 86400
        os.utime(path, (old, old))
        return path
