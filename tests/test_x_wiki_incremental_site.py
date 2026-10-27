"""Incremental strict builds match complete HTML/search and omit deleted pages."""
import json
from x_fixtures import CollectionCase
from x_wiki_site_fixtures import compile_files
from x_curator.wiki_reuse import reusable
from x_curator.wiki_links import validate


class IncrementalSiteTests(CollectionCase):
    def test_unchanged_html_search_and_changed_links_match_full_build(self):
        before={'index.md':'# Index\n\n[Stable](concepts/stable.md) [Change](concepts/change.md) [Delete](concepts/delete.md)',
                'sources/index.md':'# Sources\n','concepts/stable.md':'# Stable topic\n\nRetained searchable phrase.',
                'concepts/change.md':'# Before change\n\nOld phrase.','concepts/delete.md':'# Deleted topic\n'}
        old=compile_files(self.root,'old',before)
        after=dict(before,**{'concepts/change.md':'# After change\n\nNew searchable phrase. [Stable](stable.md)',
                             'concepts/new.md':'# Newly added\n\nNew article.'})
        after.pop('concepts/delete.md')
        after['index.md']='# Index\n\n[Stable](concepts/stable.md) [Change](concepts/change.md) [New](concepts/new.md)'
        plan=dict(root=str(self.root),manifest=old,docs=[name for name,text in after.items() if reusable(name,text.encode(),old)])
        self.assertEqual(plan['docs'],['concepts/stable.md'])
        compile_files(self.root,'incremental',after,plan)
        compile_files(self.root,'full',after)
        self.assertEqual(plan['compiled_reused'],1)
        site=self.root/'wiki/builds/incremental/site'
        full=self.root/'wiki/builds/full/site'
        for path in full.rglob('*.html'):
            self.assertEqual((site/path.relative_to(full)).read_bytes(),path.read_bytes())
        self.assertFalse((site/'concepts/delete.html').exists())
        actual=json.loads((site/'search/search_index.json').read_text())
        expected=json.loads((full/'search/search_index.json').read_text())
        self.assertEqual({v['location']:v for v in actual['docs']},{v['location']:v for v in expected['docs']})
        self.assertEqual(actual['config'],expected['config'])
        self.assertGreater(validate(site),3)
