from copy import deepcopy
import json

from x_wiki_saved_draft_fixtures import SavedDraftStoreCase
from x_curator.wiki_saved_draft_file import attach


class SavedDraftFileTests(SavedDraftStoreCase):
    def test_invalid_foreign_and_oversized_files_fail_before_any_reservation(self):
        path = self.save()
        before = '\n'.join(self.db.iterdump())
        with self.assertRaisesRegex(ValueError,'private state'):
            attach(deepcopy(self.inputs), path, self.root/'different')
        path.write_text(json.dumps(dict(pages=self.mapping['pages'], input_sha='foreign')))
        with self.assertRaisesRegex(ValueError,'only pages'):
            attach(deepcopy(self.inputs), path, self.root)
        pages = deepcopy(self.mapping['pages'])
        pages[0]['claims'] = []
        with self.assertRaises(ValueError):
            attach(deepcopy(self.inputs), self.save(pages), self.root)
        pages = deepcopy(self.mapping['pages'])
        pages[0]['description'] = 'x'*100001
        with self.assertRaisesRegex(ValueError,'proposal exceeds'):
            attach(deepcopy(self.inputs), self.save(pages), self.root)
        self.assertEqual('\n'.join(self.db.iterdump()), before)
        self.assertEqual(self.db.execute('SELECT count(*) FROM wiki_runs').fetchone()[0], 0)
