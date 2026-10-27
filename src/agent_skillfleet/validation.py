"""Explicit validation domains for source, deployed runtime, and reference tooling."""
from __future__ import annotations

import json
from pathlib import Path
import shutil
from typing import Any, Mapping

from .core import (
    FleetError,
    Paths,
    _git,
    _is_within,
    assert_locked_commit,
    cached_repo,
    first_party_skills,
    load_lock,
    load_manifest,
    manifest_items,
    runtime_skill_paths,
    validate_manifest_lock,
    validate_skill_dir,
)


def validate_source(
    paths: Paths,
    *,
    manifest: Mapping[str, Any] | None = None,
    lock: Mapping[str, Any] | None = None,
) -> list[str]:
    manifest = manifest or load_manifest(paths)
    lock = lock or load_lock(paths)
    validate_manifest_lock(paths, manifest, lock)
    first = first_party_skills(paths)
    names = [name for name, _ in first]
    if len(names) != len(set(names)):
        raise FleetError("duplicate first-party skill names")
    for _, path in first:
        validate_skill_dir(path, run_reference_validator=False)
    return ["manifest and first-party source validated; external content not materialized"]


def validate_runtime(
    paths: Paths,
    runtime: Path | None = None,
    *,
    manifest: Mapping[str, Any] | None = None,
    lock: Mapping[str, Any] | None = None,
) -> list[str]:
    manifest = manifest or load_manifest(paths)
    lock = lock or load_lock(paths)
    validate_source(paths, manifest=manifest, lock=lock)
    first = first_party_skills(paths)
    first_names = [name for name, _ in first]
    runtime = runtime or paths.active_runtime
    if not runtime.exists():
        raise FleetError(f"deployed runtime does not exist: {runtime}")
    expected = set(first_names) | {item["name"] for item in manifest_items(manifest)}
    actual = {name for name, _ in runtime_skill_paths(runtime)}
    if actual != expected:
        raise FleetError(f"runtime skill set mismatch: expected={sorted(expected)} actual={sorted(actual)}")
    metadata = runtime / ".skillfleet-meta"
    if not metadata.is_dir():
        raise FleetError(f"runtime provenance directory missing: {metadata}")
    for name in expected:
        if not (metadata / f"{name}.json").is_file():
            raise FleetError(f"runtime provenance missing for {name}")
    seen_names: set[str] = set()
    for name, link in runtime_skill_paths(runtime):
        if name in seen_names:
            raise FleetError(f"duplicate runtime skill name: {name}")
        seen_names.add(name)
        if link.is_symlink() and not link.exists():
            raise FleetError(f"broken runtime symlink: {link}")
        try:
            provenance = json.loads((metadata / f"{name}.json").read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise FleetError(f"invalid runtime provenance for {name}") from exc
        if not isinstance(provenance, dict):
            raise FleetError(f"invalid runtime provenance for {name}")
        resolved = link.resolve()
        kind = provenance.get("kind")
        trusted = runtime.resolve() if kind == "first-party" else paths.cache.resolve() if kind == "external" else None
        if trusted is None:
            raise FleetError(f"unknown runtime provenance kind for {name}: {kind!r}")
        if not _is_within(resolved, trusted):
            raise FleetError(f"runtime skill target is outside trusted {kind} root: {link} -> {resolved}")
        validate_skill_dir(resolved, run_reference_validator=False)
    for item in manifest_items(manifest):
        name = item["name"]
        entry = lock["external"][name]
        repo = cached_repo(paths, item["repo"])
        if not repo.exists():
            raise FleetError(f"external cache missing for {item['repo']}; run bootstrap")
        assert_locked_commit(repo, entry["commit"])
        _git(repo, "cat-file", "-e", f"{entry['commit']}:{item['path']}/SKILL.md")
    return [f"{len(expected)} deployed skills validated"]


def validate_reference(paths: Paths) -> list[str]:
    executable = shutil.which("skills-ref")
    if executable is None:
        raise FleetError("explicit reference validation requires the 'skills-ref' executable")
    validate_source(paths)
    messages: list[str] = []
    for name, path in first_party_skills(paths):
        result = validate_skill_dir(path, run_reference_validator=True)
        messages.extend(f"{name}: {message}" for message in result)
    return messages or ["reference validation passed"]
