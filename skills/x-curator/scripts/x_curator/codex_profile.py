"""An explicit model, subscription authentication and read-only tools for every call."""
import subprocess
import os

from .worker_errors import WorkerFailure
from .deadlines import DeadlineExceeded

MODEL = "gpt-5.6-sol"


def execution_timeout(request):
    if request.get('policy') == 'zk-organization/v1':
        return 120
    if request.get('reading', {}).get('stage') == 'composition':
        return 600
    return {'research': 900, 'organize': 900, 'organize_review': 600}.get(request['role'], 600 if request.get('reading') else 300)


def environment():
    return {key: os.environ[key] for key in ("HOME", "PATH", "USER", "LANG", "TMPDIR", "CODEX_HOME") if key in os.environ}


def command(binary, search):
    args = [binary, "--no-daemon", "exec", "--ignore-user-config", "--skip-git-repo-check",
            "--sandbox", "read-only", "--model", MODEL, "--json",
            "--enable", "skip_host_skill_discovery"]
    settings = {"forced_login_method": '"chatgpt"', "model_provider": '"openai_https"',
                "model_providers.openai_https.name": '"OpenAI"',
                "model_providers.openai_https.base_url": '"https://chatgpt.com/backend-api/codex"',
                "model_providers.openai_https.wire_api": '"responses"',
                "model_providers.openai_https.requires_openai_auth": 'true',
                "model_providers.openai_https.supports_websockets": 'false',
                "model_reasoning_effort": '"high"', "project_doc_max_bytes": "0",
                "web_search": '"live"' if search else '"disabled"'}
    for key, value in settings.items():
        args.extend(["-c", key + "=" + value])
    for feature in ("shell_tool", "apps", "plugins", "multi_agent", "browser_use", "computer_use", "hooks", "unbounded_connection_retries"):
        args.extend(["--disable", feature])
    return args


def login_status(binary, environment):
    try:
        status = subprocess.run([binary, "login", "status"], capture_output=True, timeout=15, env=environment)
    except DeadlineExceeded:
        raise
    except (subprocess.TimeoutExpired, OSError) as exc:
        raise WorkerFailure('subscription login check unavailable: ' + type(exc).__name__, b'') from exc
    if b"Logged in using ChatGPT" not in status.stdout + status.stderr:
        raise WorkerFailure("ChatGPT subscription login required; no API fallback", b"")
