"""Evidence originates in controller acquisitions, never in worker-supplied receipts."""
import json
import time
import uuid

from .leases import require_lease
from .receipts import digest, encoded, initialize
from .source_evidence import selected_source, strings
from .source_requirements import requirements
from . import blobs, x_derived, youtube_audit
from .source_currentness import currentness
from .profile_evidence import nonprofile_strings
from .source_references import reference_quotes


def capture_selection(db, token):
    initialize(db)
    job = require_lease(db, token, time.time())
    source = selected_source(db, job)
    payload = {"url": "https://x.com/i/status/" + job["id"], "kind": "selection",
               "fetched": time.time(), "source": source, "text": "\n".join(strings(source["entry"])),
               "required_urls": requirements(source["entry"])}
    return save_capture(db, token, payload)


def save_capture(db, token, payload):
    identity = uuid.uuid4().hex
    with db:
        db.execute("BEGIN IMMEDIATE")
        require_lease(db, token, time.time())
        db.execute("INSERT INTO captures VALUES (?,?,?,?)", (identity, token, encoded(payload).decode(), digest(payload)))
    return identity


def bundle(db, token):
    job = require_lease(db, token, time.time())
    return current_bundle(db, job, token)


def current_bundle(db, job, token):
    current = selected_source(db, job)
    captures = {}
    for row in db.execute("SELECT * FROM captures WHERE token=? ORDER BY id", (token,)):
        payload = json.loads(row["payload"])
        if digest(payload) != row["sha"]:
            raise ValueError("tampered capture")
        blobs.verify_payload(db, payload)
        captures[row["id"]] = payload
    # Recheck external-media provenance during reuse and publication, not only at acquisition.
    youtube_audit.verify_bundle(db, captures, job)
    from .prepared_video import verify as verify_prepared
    verify_prepared(db, captures, job)
    validate_revision(captures, current)
    evidence = {"account": job["account"], "source": job["id"], "captures": captures}
    x_derived.verify(db, evidence)
    from .quick_articles import verify as verify_articles
    verify_articles(db, evidence)
    return evidence


def validate_revision(captures, current, packet=None):
    entries = {key: c["source"]["entry"] for key, c in captures.items() if c["kind"] == "selection"}
    if not entries:
        raise ValueError("source selection was not acquired; capture it before publication")
    quotes = reference_quotes(entries, current['entry'], citation_quotes(packet, entries), packet)
    target = currentness(current["entry"], quotes)
    if any(currentness(entry, quotes) != target for entry in entries.values()):
        raise ValueError("source revision changed (content, identity, context or media); recapture and re-review")


def citation_quotes(packet, entries):
    quotes = cited_text(packet, entries)
    if not quotes:
        return ()
    outside = tuple(text for entry in entries.values() for text in nonprofile_strings(currentness(entry)[1]))
    return tuple(quote for quote in quotes if not any(quote in text for text in outside))


def cited_text(packet, selections):
    return tuple(cite['quote'] for claim in (packet or {}).get('claims', ())
                 for cite in claim['citations'] if cite.get('quote') and cite.get('capture') in selections)
