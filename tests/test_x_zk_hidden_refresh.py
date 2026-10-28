from pathlib import Path
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch
from x_zk_retained_fixtures import inputs_and_pages
from x_curator import wiki_refresh
from x_curator.receipts import digest
from x_curator.wiki_contract import validate
from x_curator.wiki_keys import page_key


class HiddenRefreshTests(TestCase):
    def test_controller_binds_only_actual_global_assignments_outside_bounded_catalog(self):
        inputs,pages = inputs_and_pages()
        inputs.pop('retained_assignments')
        inputs['catalog'] = inputs['catalog'][:1]
        current = inputs['sources']
        snapshot = SimpleNamespace(values=(current,[],{page_key(p):p for p in pages}))
        args = SimpleNamespace(publication=['source'],page=[page_key(pages[0])],reason='Synthetic refresh',state=Path('.'))
        captured = []
        def mapping(db,value):
            validate(dict(input_sha=digest(value),pages=pages[:1]),value)
            captured.append(value)
            return 'synthetic-run'
        with patch('x_curator.wiki.initial',return_value=(snapshot,None)), \
                patch('x_curator.wiki_catalog.prepare',return_value=inputs), \
                patch('x_curator.wiki_mapping.map_sources',side_effect=mapping), \
                patch('x_curator.wiki_index_result.publish',return_value={'state':'checkpoint'}), \
                patch('x_curator.wiki_input_load.Snapshot'):
            result = wiki_refresh.command(None,args)
        self.assertEqual(result['organization_run'],'synthetic-run')
        self.assertEqual(captured[0]['retained_assignments'],'catalog/v2')
        self.assertEqual(captured[0]['retained_catalog_assignments'][0]['evidence'],[{'reference':pages[1]['claims'][0]}])
