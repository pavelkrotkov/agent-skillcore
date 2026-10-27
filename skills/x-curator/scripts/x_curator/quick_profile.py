"""Expose only the local tools belonging to the current invocation's role."""
import json
from pathlib import Path
import sys

from . import blobs


def configure(args, db, token, role, native=False, linked=False, phase=None):
    profiles = {'factcheck': ('quick_mcp', ['search', 'read', 'validate']),
                'organize': ('wiki_mcp', ['context', 'validate']), 'organize_review': ('wiki_mcp', ['validate'])}
    if role not in profiles:
        return args
    module, names = profiles[role]
    from .quick_phase_tools import selected
    names = selected(names, native and role == 'factcheck', linked, phase)
    config = {'mcp_servers': '{}', 'approval_policy': '"never"',
              'mcp_servers.curator.command': json.dumps(sys.executable),
              'mcp_servers.curator.args': json.dumps(['-m', 'x_curator.' + module, str(blobs.state_root(db)), token]),
              'mcp_servers.curator.env': '{ PYTHONPATH = ' + json.dumps(str(Path(__file__).parent.parent)) + ' }',
              'mcp_servers.curator.enabled_tools': json.dumps(names),
              'mcp_servers.curator.startup_timeout_sec': '10',
              'mcp_servers.curator.tool_timeout_sec': '120',
              'mcp_servers.curator.required': 'true'}
    config.update({'mcp_servers.curator.tools.' + name + '.approval_mode': '"approve"' for name in names})
    for key, value in config.items():
        args.extend(['-c', key + '=' + value])
    return args


def checker(db, root, binary, environment):
    from functools import partial
    from .provider_recovery import invoke
    from .quick_phase_runner import capture
    invoke_final = partial(invoke, db, root, binary, environment)
    invoke_final.evidence = partial(capture, db, root, binary, environment)
    return invoke_final
