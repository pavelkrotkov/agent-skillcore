from copy import deepcopy

from x_publication_fixtures import PublicationCase
from x_curator.evidence import bundle
from x_curator.packets import validate
from x_curator.receipts import digest
from x_curator.supplemental import acquire_supplemental, limitation


class SupplementalTests(PublicationCase):
    def test_denied_optional_source_cannot_be_cited_or_hidden(self):
        url = 'https://example.org/denied'
        acquire_supplemental(self.db, self.token, {url}, lambda _: (403, 'text/plain', b'denied', None))
        evidence = bundle(self.db, self.token)
        capture = next(key for key, value in evidence['captures'].items() if value['kind'] == 'unavailable')
        packet = deepcopy(self.packet)
        packet['bundle_sha'] = digest(evidence)
        packet['coverage'].append({'capture': capture, 'status': 'unavailable', 'notes': 'HTTP denied; no claims rely on it.'})
        with self.assertRaisesRegex(ValueError, 'explicit limitation'):
            validate(packet, evidence)
        packet['limitations'] = [limitation(url)]
        validate(packet, evidence)
        packet['claims'][0]['citations'] = [{'capture': capture, 'quote': 'denied'}]
        with self.assertRaisesRegex(ValueError, 'excerpt is absent'):
            validate(packet, evidence)
