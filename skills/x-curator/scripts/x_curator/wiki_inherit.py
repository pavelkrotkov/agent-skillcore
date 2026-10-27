"""Accepted HTML remains a Markdown link target in a normal clean MkDocs build."""
from pathlib import Path
from mkdocs.plugins import BasePlugin
from mkdocs.structure.files import File
from .wiki_search import retained,merge


class AcceptedHTML(File):
    def is_documentation_page(self):
        return False


class AcceptedPages(BasePlugin):
    def __init__(self,plan):
        super().__init__()
        self.plan=plan
        self.docs=set(plan['docs'])
        self.namespace={}

    def on_files(self,files,config):
        for original in list(files.documentation_pages()):
            if original.src_uri in self.docs:
                html=original.src_uri[:-3]+'.html'
                replacement=AcceptedHTML(original.src_uri,None,config.site_dir,False,
                                         dest_uri=html,inclusion=original.inclusion)
                replacement.content_bytes=retained(self.plan,html,self.namespace)
                files.remove(original)
                files.append(replacement)
        return files

    def on_post_build(self,config):
        merge(self.plan,Path(config.site_dir)/'search/search_index.json',self.namespace)


def supported(config,nav):
    return config.nav==nav and not config.use_directory_urls and tuple(config.plugins)==('search',) and not config.plugins['search'].config.prebuild_index
