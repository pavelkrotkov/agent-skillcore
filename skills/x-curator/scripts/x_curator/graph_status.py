"""Count the recorded active graph without rebuilding it or replaying source proofs."""
import json
from pathlib import Path

from .publication_files import private_target
from .storage import sha256


def exists(db, table):
    # Status must not initialize tables or acquire a writer merely to inspect them.
    return db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone() is not None


def published_sources(db):
    return {r[0] for r in db.execute("SELECT id FROM publications WHERE state='published'")} if exists(db, "publications") else set()


def last_accepted(db):
    if not exists(db, "wiki_runs"):
        return None
    # This is the recorded start time of accepted work, not a fabricated completion time.
    row = db.execute("SELECT id,started FROM wiki_runs WHERE state='accepted' ORDER BY started DESC,id DESC LIMIT 1").fetchone()
    return dict(row) if row else None


def organization(db, root=None):
    published = published_sources(db)
    # Lightweight counts describe retained records; the separate report command audits proofs.
    value = dict(state="absent", proof_audited=False, sources_published=len(published),
                 sources_indexed=None, sources_mapped=None, sources_unmapped=None, sources_awaiting_index=None,
                 last_accepted_organization=last_accepted(db),
                 scheduling="Inspect the effective supervise --max-sources limit; zero disables organization.")
    if root is None:
        return dict(value, state="not_requested")
    try:
        manifest = current_manifest(db, root)
        if manifest is not None:
            value.update(graph_counts(root, manifest, published), state="recorded", generation=manifest["generation"])
    except (OSError, ValueError, KeyError, TypeError) as exc:
        value.update(state="unavailable", action=str(exc))
    return value


def current_manifest(db, root):
    pointer = private_target(Path(root), "wiki/CURRENT.json")
    if not pointer.exists() or (identity := json.loads(pointer.read_text())["generation"]) is None:
        return None
    # CURRENT may reuse an older retained generation; newest-created is not necessarily active.
    row = db.execute("SELECT manifest FROM wiki_builds WHERE id=?", (identity,)).fetchone()
    if row is None:
        raise ValueError("current wiki has no build receipt")
    manifest = json.loads(row[0])
    if manifest["generation"] != identity:
        raise ValueError("current wiki build identity changed")
    return manifest


def graph_counts(root, manifest, published):
    name = "wiki/builds/" + manifest["generation"] + "/site/source-map.json"
    # Read the small graph artifact without replaying historical source or model receipts.
    body = private_target(Path(root), name).read_bytes()
    if sha256(body) != manifest["files"][name]:
        raise ValueError("source-map hash differs from its build receipt")
    mapping = json.loads(body)
    indexed = set(manifest["sources"])
    # Matching membership prevents mixing counts from different indexing generations.
    if set(mapping) != indexed:
        raise ValueError("source-map membership differs from its build receipt")
    mapped = sum(bool(mapping[source]) for source in indexed)
    return dict(sources_indexed=len(indexed), sources_mapped=mapped, sources_unmapped=len(indexed)-mapped,
                sources_awaiting_index=len(published-indexed))
