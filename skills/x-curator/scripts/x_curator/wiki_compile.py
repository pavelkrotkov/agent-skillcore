"""Qualified strict compiler; unchanged pages use the supported File/plugin API."""
import json
import os
import subprocess
import sys
from pathlib import Path
from importlib.metadata import version
from .receipts import encoded

NAV=[{'Knowledge':'index.md'},{'Sources':'sources/index.md'}]



def stack():
    return {name:version(name) for name in ('mkdocs','Markdown','Jinja2','MarkupSafe','PyYAML')}


def invoke(config_path,reuse):
    if version('mkdocs')!='1.6.1':
        raise ValueError('wiki compiler differs from qualified version')
    command=[sys.executable,'-m',__name__,str(config_path)]
    if reuse is not None:
        command.append('--inherit')
    result=subprocess.run(command,input=encoded(reuse) if reuse is not None else None,
                          capture_output=True,check=True,timeout=120,env=dict(os.environ,SOURCE_DATE_EPOCH='0',PYTHONPATH=str(Path(__file__).resolve().parent.parent)))
    if reuse is not None:
        reuse['compiled_reused']=json.loads(result.stdout)['reused_html']


def compile_site(config_path,inherit=False):
    from mkdocs.config import load_config
    from mkdocs.commands.build import build
    from .wiki_inherit import AcceptedPages,supported
    config=load_config(config_file=config_path,strict=True)
    reused=0
    if inherit and supported(config,NAV):
        plan=json.loads(sys.stdin.buffer.read())
        config.plugins['accepted-pages']=AcceptedPages(plan)
        reused=len(plan['docs'])
    build(config)
    print(json.dumps(dict(reused_html=reused)))


if __name__=='__main__':
    compile_site(sys.argv[1],len(sys.argv)>2)
