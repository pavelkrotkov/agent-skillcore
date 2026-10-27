import json

from x_linked_fixtures import LinkedCase
from x_quick_fixtures import native
from x_curator import quick_mcp
from x_curator.publication_audit import audit
from x_curator.receipts import digest


class LinkedSourcesTests(LinkedCase):
    urls = ['https://example.test/release', 'https://example.test/version']

    def checker(self, request):
        self.request = request
        log = self.root / 'runs' / self.token / (digest(request) + '.jsonl')
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_bytes(b'')
        self.assertEqual(set(request['sources'].values()), set(self.urls))
        prefetched = [c['url'] for c in request['bundle']['captures'].values() if c['kind'] == 'text']
        self.assertEqual(prefetched, [self.urls[0]])
        read = quick_mcp.call(self.db, self.token, 'read', {'source': self.urls[1]})
        self.assertFalse(read['isError'], read)
        capture = json.loads(read['content'][0]['text'])['capture']
        decision = self.supported(request)
        decision['claims'][0]['sources'][0]['capture'] = capture
        self.validation = quick_mcp.call(self.db, self.token, 'validate', {'decision': decision})
        return native(request, decision, [read, self.validation])

    def test_second_link_can_be_read_and_cited_after_first_link_prefetch(self):
        self.assertEqual(self.run_worker()['completed'], 1)
        self.assertFalse(self.validation['isError'])
        self.assertEqual(audit(self.db, self.root), [])
        check = self.db.execute('SELECT * FROM quick_checks').fetchone()
        self.assertEqual(check['deadline'] - check['started'], 120)
        self.assertEqual(self.db.execute('SELECT count(*) FROM executions').fetchone()[0], 1)
