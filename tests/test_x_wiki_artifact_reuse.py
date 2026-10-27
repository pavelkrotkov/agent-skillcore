"""Immutable document reuse and HTML facts retain actual-byte and target checks."""
import json
from x_fixtures import CollectionCase
from x_curator import wiki_markdown,wiki_store
from x_curator.publication_files import write_verified
from x_curator.storage import sha256
from x_curator.wiki_files import activate


class ArtifactReuseTests(CollectionCase):
    def previous(self):
        wiki_store.initialize(self.db)
        path='wiki/builds/old/docs/page.md'
        write_verified(self.root,path,b'unchanged')
        manifest=dict(generation='old',files={path:sha256(b'unchanged')})
        self.db.execute('INSERT INTO wiki_builds VALUES (?,?,?)',('old',json.dumps(manifest),0))
        self.db.commit()
        activate(self.root,'old')
        return self.root/path

    def test_unchanged_documents_are_linked_and_changed_bytes_are_rejected(self):
        old=self.previous()
        wiki_markdown.write(self.db,self.root,'wiki/builds/new',{'page.md':b'unchanged','fresh.md':b'new'})
        new=self.root/'wiki/builds/new/docs/page.md'
        self.assertEqual(old.stat().st_ino,new.stat().st_ino)
        self.assertEqual((new.parent/'fresh.md').read_bytes(),b'new')
        old.write_bytes(b'corrupted')
        with self.assertRaisesRegex(ValueError,'inherited wiki Markdown'):
            wiki_markdown.write(self.db,self.root,'wiki/builds/rejected',{'page.md':b'unchanged'})


    def test_destination_symlink_and_parent_escape_cannot_receive_documents(self):
        old=self.previous()
        folder=self.root/'wiki/builds/rejected/docs'
        folder.mkdir(parents=True)
        (folder/'escape').symlink_to(old.parent,target_is_directory=True)
        with self.assertRaisesRegex(ValueError,'symlink'):
            wiki_markdown.write(self.db,self.root,'wiki/builds/rejected',{'escape/unexpected.md':b'wrong'})
        with self.assertRaisesRegex(ValueError,'escaped'):
            wiki_markdown.write(self.db,self.root,'wiki/builds/rejected',{'../../unexpected.md':b'wrong'})
        self.assertFalse((old.parent/'unexpected.md').exists())
