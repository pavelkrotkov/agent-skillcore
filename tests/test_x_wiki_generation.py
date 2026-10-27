from x_wiki_fixtures import WikiCase
from x_curator.receipts import digest
from x_curator.storage import sha256
from x_curator.wiki_build import build
from x_curator.wiki_render import render
from x_curator.publication_files import write_verified
from x_curator.wiki_site import render_site


class WikiGenerationTests(WikiCase):
    def test_old_rendering_policy_cannot_reuse_previous_generation(self):
        manifest = build(self.db, self.root, self.sources, {})
        legacy_policy = dict(manifest['policy'], renderer=1)
        legacy_identity = digest({'policy': legacy_policy, 'files': {
            name: sha256(body) for name, body in render(self.sources, {}).items()}})
        self.assertNotEqual(manifest['generation'], legacy_identity)

    def test_strict_compiler_is_reproducible_across_generation_paths(self):
        for identity in ('one','two'):
            prefix='wiki/builds/'+identity
            for name in ('index.md','sources/index.md','page.md'):
                write_verified(self.root,prefix+'/docs/'+name,b'# Stable title\n\nStable body.\n')
            render_site(self.root,prefix)
        one=self.root/'wiki/builds/one/site'
        two=self.root/'wiki/builds/two/site'
        for path in one.rglob('*.html'):
            self.assertEqual(path.read_bytes(),(two/path.relative_to(one)).read_bytes())
