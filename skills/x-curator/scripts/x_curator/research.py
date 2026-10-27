"""One source moves through acquisition, research, independent review and readback."""
import json

from .acquire import acquire_urls
from .x_urls import source_fetcher
from .codex_profile import MODEL
from .codex_runner import runner
from .evidence import bundle, capture_selection
from .executions import execute
from .packets import validate
from .publication import publish
from .review_feedback import previous_rejection
from .supplemental import acquire_supplemental
from . import reading_discovery, reading_work


def research(db, state, client, token):
    capture_selection(db, token)
    call = runner(db, token)
    fetcher = source_fetcher(client)
    initial = bundle(db, token)
    required = {url for c in initial["captures"].values() for url in c.get("required_urls", [])}
    required.add("https://x.com/i/status/" + initial["source"])
    acquire_urls(db, token, required, fetcher)
    discovery = reading_discovery.discover(db, token, call)
    acquire_discovery(db, token, discovery, fetcher)
    if reading_work.required(bundle(db, token)):
        return reading_work.run(db, state, token, call)
    proposal = execute(db, token, "research", MODEL, call, feedback=previous_rejection(db, token))
    packet = output(db, proposal)
    validate(packet, bundle(db, token))
    review = execute(db, token, "review", MODEL, call, packet)
    return publish(db, state, token, proposal, review)


def output(db, execution):
    return json.loads(db.execute("SELECT output FROM executions WHERE id=?", (execution,)).fetchone()[0])


def acquire_discovery(db, token, execution, fetcher):
    discovery = output(db, execution)
    urls = discovery["urls"]
    if not isinstance(urls, list) or len(urls) > 5:
        raise ValueError("discovery exceeds five supplemental sources")
    evidence = bundle(db, token)
    acquired = {c["url"] for c in evidence["captures"].values()}
    acquire_supplemental(db, token, set(urls) - acquired, fetcher)
