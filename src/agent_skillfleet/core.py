"""Core operations for the Skillfleet command-line tools.

The module intentionally keeps the public surface small.  The shell scripts in
``bin/`` are only adapters; tests exercise these functions through the CLI and
through the filesystem they manage.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any, Iterable, Mapping
from urllib.parse import urlparse

try:
    import yaml
except ImportError:  # pragma: no cover - exercised by a fresh-machine CLI error
    yaml = None  # type: ignore[assignment]


HEX40 = re.compile(r"^[0-9a-f]{40}$")
SKILL_NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
PRIVATE_KEY = re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----")
SECRET_PATTERNS = (
    PRIVATE_KEY,
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\b(?:ghp|gho|github_pat)_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"),
)


class FleetError(RuntimeError):
    """An expected, user-actionable failure."""


def _need_yaml() -> Any:
    if yaml is None:
        raise FleetError("PyYAML is required; run 'python3 -m pip install -e .[test]' or run bin/bootstrap")
    return yaml


def _json_dump(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True) + "\n"


def _yaml_dump(value: Mapping[str, Any]) -> str:
    return _need_yaml().safe_dump(value, sort_keys=False, default_flow_style=False)


def _read_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FleetError(f"missing YAML file: {path}")
    yaml_module = _need_yaml()
    try:
        value = yaml_module.safe_load(path.read_text(encoding="utf-8"))
    except yaml_module.YAMLError as exc:
        raise FleetError(f"invalid YAML in {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise FleetError(f"{path} must contain a YAML mapping")
    return value


def _write_text_atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
        os.replace(temp_name, path)
    except BaseException:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise


def _run(
    args: list[str],
    *,
    cwd: Path | None = None,
    check: bool = True,
    capture: bool = True,
    env: Mapping[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    try:
        result = subprocess.run(
            args,
            cwd=cwd,
            env=dict(env) if env else None,
            check=False,
            text=True,
            stdout=subprocess.PIPE if capture else None,
            stderr=subprocess.PIPE if capture else None,
        )
    except OSError as exc:
        raise FleetError(f"could not run {' '.join(args)}: {exc}") from exc
    if check and result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        raise FleetError(f"command failed ({result.returncode}): {' '.join(args)}\n{detail}")
    return result


def _git(root: Path, *args: str, check: bool = True) -> str:
    result = _run(["git", "-C", str(root), *args], check=check)
    return (result.stdout or "").strip()


def _is_within(path: Path, parent: Path) -> bool:
    try:
        path.resolve(strict=False).relative_to(parent.resolve(strict=False))
        return True
    except ValueError:
        return False


def _safe_relative(name: str) -> bool:
    path = Path(name)
    return not path.is_absolute() and ".." not in path.parts


@dataclass(frozen=True)
class Paths:
    repo: Path
    runtime: Path
    cache: Path
    state: Path

    @classmethod
    def from_environment(cls, repo: Path | None = None) -> "Paths":
        repo = (repo or Path.cwd()).resolve()
        home = Path.home()
        data_home = Path(os.environ.get("XDG_DATA_HOME", home / ".local" / "share"))
        cache_home = Path(os.environ.get("XDG_CACHE_HOME", home / ".cache"))
        state_home = Path(os.environ.get("XDG_STATE_HOME", home / ".local" / "state"))
        return cls(
            repo=repo,
            runtime=Path(os.environ.get("AGENT_SKILLFLEET_RUNTIME", data_home / "agent-skillfleet-runtime")),
            cache=Path(os.environ.get("AGENT_SKILLFLEET_CACHE", cache_home / "agent-skillfleet")),
            state=Path(os.environ.get("AGENT_SKILLFLEET_STATE", state_home / "agent-skillfleet")),
        )

    @property
    def manifest(self) -> Path:
        return self.repo / "external" / "skills.yaml"

    @property
    def lockfile(self) -> Path:
        return self.repo / "external" / "skills.lock"

    @property
    def overrides(self) -> Path:
        return self.repo / "overrides"

    @property
    def active_runtime(self) -> Path:
        return self.runtime / "current"


def load_manifest(paths: Paths) -> dict[str, Any]:
    manifest = _read_yaml(paths.manifest)
    if manifest.get("version") != 1:
        raise FleetError(f"{paths.manifest}: version must be 1")
    external = manifest.get("external", [])
    if not isinstance(external, list):
        raise FleetError(f"{paths.manifest}: external must be a list")
    names: set[str] = set()
    for item in external:
        if not isinstance(item, dict):
            raise FleetError("each external skill must be a mapping")
        for key in ("name", "repo", "path"):
            if not isinstance(item.get(key), str) or not item[key].strip():
                raise FleetError(f"external skill is missing a non-empty {key}")
        name = item["name"]
        if not SKILL_NAME.fullmatch(name):
            raise FleetError(f"invalid external skill name: {name!r}")
        if name in names:
            raise FleetError(f"duplicate external skill name: {name}")
        names.add(name)
        if not _safe_relative(item["path"]):
            raise FleetError(f"external skill path must be relative and safe: {item['path']!r}")
        track = item.get("track", {})
        if track is not None and not isinstance(track, dict):
            raise FleetError(f"{name}: track must be a mapping")
        deployment = item.get("deployment", {})
        if deployment is not None and not isinstance(deployment, dict):
            raise FleetError(f"{name}: deployment must be a mapping")
        native = item.get("native", {})
        if native is not None and not isinstance(native, dict):
            raise FleetError(f"{name}: native must be a mapping")
        for agent, config in (native or {}).items():
            if agent not in {"codex", "claude", "hermes"} or not isinstance(config, dict):
                raise FleetError(f"{name}: native entries must be codex/claude/hermes mappings")
            for op in ("install", "update", "check"):
                if op in config and config[op] is not None and not isinstance(config[op], str):
                    raise FleetError(f"{name}: native.{agent}.{op} must be a string")
    return manifest


def load_lock(paths: Paths) -> dict[str, Any]:
    lock = _read_yaml(paths.lockfile)
    if lock.get("version") != 1:
        raise FleetError(f"{paths.lockfile}: version must be 1")
    external = lock.get("external", {})
    if not isinstance(external, dict):
        raise FleetError(f"{paths.lockfile}: external must be a mapping")
    return lock


def first_party_skills(paths: Paths) -> list[tuple[str, Path]]:
    root = paths.repo / "skills"
    if not root.exists():
        return []
    result: list[tuple[str, Path]] = []
    for child in sorted(root.iterdir(), key=lambda p: p.name):
        if not child.is_dir() or child.is_symlink():
            continue
        if (child / "SKILL.md").is_file():
            result.append((child.name, child))
    return result


def manifest_items(manifest: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [dict(item) for item in manifest.get("external", [])]


def validate_manifest_lock(paths: Paths, manifest: Mapping[str, Any] | None = None, lock: Mapping[str, Any] | None = None) -> None:
    manifest = manifest or load_manifest(paths)
    lock = lock or load_lock(paths)
    locked = lock.get("external", {})
    expected_names = {item["name"] for item in manifest_items(manifest)}
    if set(locked) != expected_names:
        missing = sorted(expected_names - set(locked))
        extra = sorted(set(locked) - expected_names)
        detail = []
        if missing:
            detail.append(f"missing={','.join(missing)}")
        if extra:
            detail.append(f"extra={','.join(extra)}")
        raise FleetError(f"manifest/lock mismatch ({'; '.join(detail)})")
    for item in manifest_items(manifest):
        entry = locked[item["name"]]
        if not isinstance(entry, dict):
            raise FleetError(f"lock entry {item['name']} must be a mapping")
        for key in ("repo", "path"):
            if entry.get(key) != item[key]:
                raise FleetError(f"lock entry {item['name']} does not match manifest field {key}")
        commit = entry.get("commit")
        if not isinstance(commit, str) or not HEX40.fullmatch(commit):
            raise FleetError(f"{item['name']}: commit must be a 40-character lowercase Git SHA")
        if not _safe_relative(item["path"]):
            raise FleetError(f"{item['name']}: unsafe path")


def repo_cache_key(repo: str) -> str:
    parsed = urlparse(repo)
    if parsed.scheme == "file":
        return f"local-{hashlib.sha256(repo.encode()).hexdigest()[:16]}"
    if parsed.scheme in {"http", "https", "ssh"} and parsed.netloc:
        path = parsed.path.strip("/").removesuffix(".git")
        if path:
            return f"{parsed.netloc}/{path}"
    if repo.startswith("git@") and ":" in repo:
        host, path = repo.split(":", 1)
        return f"{host[4:]}/{path.removesuffix('.git')}"
    return f"local-{hashlib.sha256(repo.encode()).hexdigest()[:16]}"


def cached_repo(paths: Paths, repo: str) -> Path:
    key = repo_cache_key(repo)
    return paths.cache / "repos" / key


def ensure_repo_cache(paths: Paths, repo: str, *, fetch: bool = True) -> Path:
    destination = cached_repo(paths, repo)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not (destination / ".git").exists():
        if destination.exists() and any(destination.iterdir()):
            raise FleetError(f"cache path exists but is not a Git repository: {destination}")
        _run(["git", "clone", "--no-checkout", repo, str(destination)])
        return destination
    if fetch:
        _git(destination, "fetch", "--all", "--tags", "--prune")
    return destination


def locked_commit_exists(repo: Path, commit: str) -> bool:
    result = _run(["git", "-C", str(repo), "cat-file", "-e", f"{commit}^{{commit}}"], check=False)
    return result.returncode == 0


def assert_locked_commit(repo: Path, commit: str) -> None:
    if not HEX40.fullmatch(commit):
        raise FleetError(f"invalid commit {commit!r}")
    if not locked_commit_exists(repo, commit):
        raise FleetError(f"locked commit {commit} is not available in {repo}; fetch the repository")


def tracked_revision(repo: Path, track: Mapping[str, Any] | None) -> str:
    track = track or {"branch": "main"}
    if "branch" in track:
        branch = str(track["branch"])
        ref = f"refs/remotes/origin/{branch}"
        if not locked_commit_exists(repo, _git(repo, "rev-parse", ref, check=False)):
            result = _run(["git", "-C", str(repo), "rev-parse", "--verify", ref], check=False)
            if result.returncode != 0:
                raise FleetError(f"tracked branch {branch!r} is not present in cached repository {repo}")
        return _git(repo, "rev-parse", f"{ref}^{{commit}}")
    if "tag" in track:
        tag = str(track["tag"])
        return _git(repo, "rev-parse", f"refs/tags/{tag}^{{commit}}")
    raise FleetError("track must contain branch or tag")


def _extract_tar(data: bytes, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    with tarfile.open(fileobj=BytesIO(data), mode="r:") as archive:
        members = archive.getmembers()
        for member in members:
            if not _safe_relative(member.name):
                raise FleetError(f"upstream archive contains unsafe path: {member.name}")
        archive.extractall(destination)


def materialized_external(paths: Paths, repo: Path, repo_url: str, path: str, commit: str) -> Path:
    assert_locked_commit(repo, commit)
    cache_path = paths.cache / "materialized" / repo_cache_key(repo_url) / commit / path
    marker = cache_path.with_name(f"{cache_path.name}.source.json")
    if marker.exists() and (cache_path / "SKILL.md").is_file():
        return cache_path
    if cache_path.exists():
        shutil.rmtree(cache_path)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        _git(repo, "cat-file", "-e", f"{commit}:{path}/SKILL.md")
    except FleetError as exc:
        raise FleetError(f"external skill path does not exist at {repo_url}@{commit}: {path}") from exc
    try:
        archive_bytes = subprocess.run(
            ["git", "-C", str(repo), "archive", "--format=tar", f"{commit}:{path}"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        ).stdout
    except subprocess.CalledProcessError as exc:
        detail = exc.stderr.decode(errors="replace").strip()
        raise FleetError(f"could not archive {repo_url}@{commit}:{path}: {detail}") from exc
    _extract_tar(archive_bytes, cache_path)
    _write_text_atomic(marker, _json_dump({"repo": repo_url, "path": path, "commit": commit}))
    if not (cache_path / "SKILL.md").is_file():
        raise FleetError(f"could not materialize external skill path {path} at {commit}")
    return cache_path


def _patches_for(paths: Paths, skill_name: str) -> list[Path]:
    override = paths.overrides / skill_name
    series = override / "series"
    if not series.exists():
        return []
    result: list[Path] = []
    for raw in series.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        patch = (override / line).resolve()
        if not _is_within(patch, override.resolve()) or not patch.is_file():
            raise FleetError(f"invalid override patch for {skill_name}: {line}")
        result.append(patch)
    return result


def apply_patches(paths: Paths, skill_name: str, source: Path) -> list[str]:
    patches = _patches_for(paths, skill_name)
    applied: list[str] = []
    for patch in patches:
        _run(["git", "-C", str(source), "apply", "--check", str(patch)])
        _run(["git", "-C", str(source), "apply", str(patch)])
        applied.append(str(patch.relative_to((paths.overrides / skill_name).resolve())))
    return applied


def patch_digests(paths: Paths, skill_name: str) -> list[dict[str, str]]:
    result = []
    for patch in _patches_for(paths, skill_name):
        result.append(
            {
                "path": str(patch.relative_to((paths.overrides / skill_name).resolve())),
                "sha256": hashlib.sha256(patch.read_bytes()).hexdigest(),
            }
        )
    return result


def _repo_origin(paths: Paths) -> str:
    result = _run(["git", "-C", str(paths.repo), "config", "--get", "remote.origin.url"], check=False)
    return (result.stdout or "").strip() or str(paths.repo)


def _first_party_commit(paths: Paths) -> str:
    result = _run(["git", "-C", str(paths.repo), "rev-parse", "HEAD"], check=False)
    return (result.stdout or "").strip() or "working-tree"


def _release_id(sources: list[Mapping[str, Any]], first_party_commit: str) -> str:
    encoded = json.dumps(
        {"runtime_format": 2, "first_party": first_party_commit, "sources": sources}, sort_keys=True
    ).encode()
    return hashlib.sha256(encoded).hexdigest()[:20]


def _link(target: Path, link: Path) -> None:
    link.parent.mkdir(parents=True, exist_ok=True)
    os.symlink(str(target), str(link))


def assemble_runtime(
    paths: Paths,
    *,
    activate: bool = False,
    runtime: Path | None = None,
    manifest: Mapping[str, Any] | None = None,
    lock: Mapping[str, Any] | None = None,
) -> Path:
    manifest = manifest or load_manifest(paths)
    lock = lock or load_lock(paths)
    validate_manifest_lock(paths, manifest, lock)
    runtime = runtime or paths.runtime
    runtime.mkdir(parents=True, exist_ok=True)
    releases = runtime / "releases"
    releases.mkdir(parents=True, exist_ok=True)

    names: dict[str, str] = {}
    for name, _ in first_party_skills(paths):
        names[name] = "first-party"
    for item in manifest_items(manifest):
        name = item["name"]
        if name in names:
            raise FleetError(f"skill name collision: {name} ({names[name]} and external)")
        names[name] = "external"

    source_records: list[dict[str, Any]] = []
    stage = Path(tempfile.mkdtemp(prefix=".stage-", dir=runtime))
    try:
        metadata = stage / ".skillfleet-meta"
        metadata.mkdir()
        for name, source in first_party_skills(paths):
            target = source.resolve()
            if not _is_within(target, (paths.repo / "skills").resolve()):
                raise FleetError(f"first-party skill escapes skills/: {source}")
            shutil.copytree(target, stage / name)
            record = {
                "kind": "first-party",
                "repository": _repo_origin(paths),
                "commit": _first_party_commit(paths),
                "path": str(source.relative_to(paths.repo)),
                "patches": [],
            }
            _write_text_atomic(metadata / f"{name}.json", _json_dump(record))
            source_records.append({"name": name, **record})
        for item in manifest_items(manifest):
            name, repo_url, source_path = item["name"], item["repo"], item["path"]
            lock_entry = lock["external"][name]
            repo = ensure_repo_cache(paths, repo_url)
            materialized = materialized_external(paths, repo, repo_url, source_path, lock_entry["commit"])
            digests = patch_digests(paths, name)
            if digests:
                patch_key = hashlib.sha256(json.dumps(digests, sort_keys=True).encode()).hexdigest()[:20]
                patched = paths.cache / "patched" / repo_cache_key(repo_url) / lock_entry["commit"] / name / patch_key
                patch_marker = patched.with_name(f"{patched.name}.json")
                ready = False
                if patched.exists() and patch_marker.is_file():
                    try:
                        ready = json.loads(patch_marker.read_text(encoding="utf-8")) == digests
                    except (OSError, json.JSONDecodeError):
                        ready = False
                if not ready:
                    if patched.exists():
                        shutil.rmtree(patched)
                    if patch_marker.exists():
                        patch_marker.unlink()
                    patched.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copytree(materialized, patched)
                    applied = apply_patches(paths, name, patched)
                    _write_text_atomic(patch_marker, _json_dump(digests))
                else:
                    applied = [entry["path"] for entry in digests]
                target = patched.resolve()
            else:
                applied = []
                target = materialized.resolve()
            if not _is_within(target, paths.cache.resolve()):
                raise FleetError(f"external skill escapes cache: {target}")
            _link(target, stage / name)
            record = {
                "kind": "external",
                "source": repo_url,
                "path": source_path,
                "commit": lock_entry["commit"],
                "patches": applied,
                "patch_digests": digests,
            }
            _write_text_atomic(metadata / f"{name}.json", _json_dump(record))
            source_records.append({"name": name, **record})
        release = releases / _release_id(source_records, _first_party_commit(paths))
        if release.exists():
            shutil.rmtree(stage)
        else:
            os.replace(stage, release)
        if activate:
            activate_runtime(runtime, release)
        return release
    except BaseException:
        if stage.exists():
            shutil.rmtree(stage)
        raise


def activate_runtime(runtime: Path, release: Path) -> None:
    runtime.mkdir(parents=True, exist_ok=True)
    current_new = runtime / ".current.new"
    try:
        if current_new.is_symlink() or current_new.exists():
            current_new.unlink()
        os.symlink(str(release), str(current_new))
        os.replace(current_new, runtime / "current")
    finally:
        if current_new.is_symlink() or current_new.exists():
            current_new.unlink()


def _frontmatter(skill_file: Path) -> dict[str, Any]:
    text = skill_file.read_text(encoding="utf-8")
    if not text.startswith("---"):
        raise FleetError(f"{skill_file}: missing YAML frontmatter")
    parts = text.split("---", 2)
    if len(parts) != 3:
        raise FleetError(f"{skill_file}: malformed YAML frontmatter")
    yaml_module = _need_yaml()
    try:
        value = yaml_module.safe_load(parts[1])
    except yaml_module.YAMLError as exc:
        raise FleetError(f"{skill_file}: invalid frontmatter: {exc}") from exc
    if not isinstance(value, dict):
        raise FleetError(f"{skill_file}: frontmatter must be a mapping")
    return value


def validate_skill_dir(path: Path, *, run_reference_validator: bool = False) -> list[str]:
    skill_file = path / "SKILL.md"
    if not skill_file.is_file():
        raise FleetError(f"skill is missing SKILL.md: {path}")
    frontmatter = _frontmatter(skill_file)
    name = frontmatter.get("name")
    description = frontmatter.get("description")
    if not isinstance(name, str) or not SKILL_NAME.fullmatch(name):
        raise FleetError(f"{skill_file}: invalid name")
    if name != path.name:
        raise FleetError(f"{skill_file}: name {name!r} does not match directory {path.name!r}")
    if not isinstance(description, str) or not description.strip() or len(description) > 1024:
        raise FleetError(f"{skill_file}: description must be non-empty and at most 1024 characters")
    compatibility = frontmatter.get("compatibility")
    if compatibility is not None and (not isinstance(compatibility, str) or len(compatibility) > 500):
        raise FleetError(f"{skill_file}: compatibility must be at most 500 characters")
    secrets: list[str] = []
    for child in path.rglob("*"):
        if not child.is_file() or child.is_symlink():
            continue
        try:
            content = child.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if any(pattern.search(content) for pattern in SECRET_PATTERNS):
            secrets.append(str(child))
    if secrets:
        raise FleetError(f"possible secret material in skill: {', '.join(secrets)}")
    messages: list[str] = []
    if run_reference_validator:
        validator_tool = shutil.which("skills-ref")
        if validator_tool is None:
            raise FleetError("skills-ref is required for reference validation but is not on PATH")
        result = _run([validator_tool, "validate", str(path)], check=False)
        if result.returncode != 0:
            error_msg = (result.stdout or result.stderr or "skills-ref validation failed").strip()
            raise FleetError(error_msg)
        messages.append("skills-ref passed")
    return messages


def runtime_skill_paths(runtime: Path) -> list[tuple[str, Path]]:
    if not runtime.exists():
        raise FleetError(f"runtime does not exist: {runtime}")
    result = []
    for child in sorted(runtime.iterdir(), key=lambda p: p.name):
        if child.name.startswith(".") or child.name in {"releases", "current"}:
            continue
        if child.is_symlink() or child.is_dir():
            result.append((child.name, child))
    return result


def validate_runtime(
    paths: Paths,
    runtime: Path | None = None,
    *,
    manifest_only: bool = False,
    manifest: Mapping[str, Any] | None = None,
    lock: Mapping[str, Any] | None = None,
) -> list[str]:
    manifest = manifest or load_manifest(paths)
    lock = lock or load_lock(paths)
    validate_manifest_lock(paths, manifest, lock)
    first = first_party_skills(paths)
    first_names = [name for name, _ in first]
    if len(first_names) != len(set(first_names)):
        raise FleetError("duplicate first-party skill names")
    if manifest_only:
        for name, path in first:
            validate_skill_dir(path, run_reference_validator=False)
        return ["manifest and first-party source validated; external content not materialized"]
    runtime = runtime or paths.active_runtime
    if not runtime.exists():
        return validate_runtime(paths, runtime, manifest_only=True, manifest=manifest, lock=lock)
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
        if kind == "first-party":
            trusted = runtime.resolve()
        elif kind == "external":
            trusted = paths.cache.resolve()
        else:
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
    return [f"{len(expected)} skills validated"]


def _marker_path(directory: Path) -> Path:
    return directory / ".agent-skillfleet-managed"


def _read_marker(directory: Path) -> list[str]:
    marker = _marker_path(directory)
    if not marker.is_file():
        return []
    try:
        value = json.loads(marker.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    return [str(name) for name in value.get("skills", [])] if isinstance(value, dict) else []


def _agent_directories() -> dict[str, Path]:
    home = Path.home()
    return {
        "codex": Path(os.environ.get("AGENT_SKILLFLEET_CODEX_DIR", home / ".agents" / "skills")),
        "claude": Path(os.environ.get("AGENT_SKILLFLEET_CLAUDE_DIR", home / ".claude" / "skills")),
    }


def install_links(paths: Paths, *, dry_run: bool = False) -> list[str]:
    runtime = paths.active_runtime
    if not runtime.is_dir():
        raise FleetError(f"active runtime is missing: {runtime}; run bootstrap first")
    skill_names = [name for name, _ in runtime_skill_paths(runtime)]
    desired = {name: runtime / name for name in skill_names}
    messages: list[str] = []
    directories = _agent_directories()
    plans: list[tuple[Path, str, Path | None, str]] = []
    for agent, directory in directories.items():
        previous = set(_read_marker(directory))
        for stale in sorted(previous - set(desired)):
            link = directory / stale
            if link.is_symlink():
                plans.append((link, "remove", None, agent))
            elif link.exists():
                messages.append(f"! {agent}: preserving non-symlink stale entry {link}")
        for name, target in desired.items():
            link = directory / name
            if link.is_symlink():
                existing_target = (directory / os.readlink(link)).resolve() if not os.path.isabs(os.readlink(link)) else Path(os.readlink(link)).resolve()
                if existing_target == target.resolve():
                    messages.append(f"✓ {agent}: {name} already linked")
                elif name in previous:
                    plans.append((link, "replace", target, agent))
                else:
                    raise FleetError(f"refusing to replace unrelated symlink {link}; remove it manually")
            elif link.exists():
                raise FleetError(f"refusing to replace unrelated file or directory {link}")
            else:
                plans.append((link, "create", target, agent))
    if not dry_run:
        for directory in directories.values():
            directory.mkdir(parents=True, exist_ok=True)
        for link, action, target, agent in plans:
            if action in {"replace", "remove"}:
                link.unlink()
            if action != "remove" and target is not None:
                os.symlink(str(target), str(link))
            messages.append(f"✓ {agent}: {action}d {link.name}")
        for agent, directory in directories.items():
            _write_text_atomic(_marker_path(directory), _json_dump({"version": 1, "skills": sorted(desired)}))
    else:
        messages.extend(f"would {action} {agent}:{link.name}" for link, action, _, agent in plans)
    hermes_fragment = paths.state / "hermes" / "external-skills.yaml"
    fragment = {"skills": {"external_dirs": [str(paths.active_runtime)]}}
    if not dry_run:
        _write_text_atomic(hermes_fragment, _yaml_dump(fragment))
        messages.append(f"✓ Hermes fragment: {hermes_fragment}")
    else:
        messages.append(f"would write Hermes fragment: {hermes_fragment}")
    return messages


def check_dirty(paths: Paths) -> bool:
    return bool(_git(paths.repo, "status", "--porcelain"))


def check_main_synced(paths: Paths) -> list[str]:
    messages = []
    branch = _git(paths.repo, "branch", "--show-current")
    if branch != "main":
        raise FleetError(f"refusing sync from branch {branch or '(detached)'}; checkout clean main")
    origin = _run(["git", "-C", str(paths.repo), "config", "--get", "remote.origin.url"], check=False)
    if not (origin.stdout or "").strip():
        raise FleetError("canonical checkout has no origin remote")
    _git(paths.repo, "fetch", "origin", "main")
    _git(paths.repo, "merge", "--ff-only", "origin/main")
    messages.append("✓ canonical checkout is clean and fast-forwarded")
    return messages



def doctor(paths: Paths, *, fetch: bool = False) -> tuple[list[str], int]:
    lines: list[str] = ["Skillfleet root"]
    errors = 0
    lines.append(f"  ✓ {paths.repo}")
    try:
        if check_dirty(paths):
            lines.append("  ! git checkout dirty")
        else:
            lines.append("  ✓ git checkout clean")
        branch = _git(paths.repo, "branch", "--show-current")
        lines.append(f"  {'✓' if branch == 'main' else '!'} branch {branch or '(detached)'}")
    except FleetError as exc:
        lines.append(f"  ✗ git: {exc}")
        errors += 1
    try:
        manifest = load_manifest(paths)
        lock = load_lock(paths)
        validate_manifest_lock(paths, manifest, lock)
        lines.append(f"  ✓ manifest and lockfile agree ({len(manifest_items(manifest))} external skills)")
    except FleetError as exc:
        lines.append(f"  ✗ dependencies: {exc}")
        errors += 1
    try:
        messages = validate_runtime(paths)
        lines.extend(f"  ✓ {message}" for message in messages)
    except FleetError as exc:
        lines.append(f"  ✗ runtime: {exc}")
        errors += 1
    for agent, directory in _agent_directories().items():
        marker = _read_marker(directory)
        if marker:
            lines.append(f"  ✓ {agent}: {len(marker)} managed links recorded at {directory}")
        else:
            lines.append(f"  ! {agent}: no Skillfleet managed-link marker at {directory}")
    fragment = paths.state / "hermes" / "external-skills.yaml"
    if fragment.is_file():
        lines.append(f"  ✓ Hermes fragment available: {fragment}")
    else:
        lines.append("  ! Hermes: install the generated external_dirs fragment if desired")
    lines.append("  ✓ filesystem exposure checked; semantic agent loading is not claimed")
    if fetch:
        try:
            for item in manifest_items(load_manifest(paths)):
                repo = ensure_repo_cache(paths, item["repo"])
                upstream = tracked_revision(repo, item.get("track"))
                locked = load_lock(paths)["external"][item["name"]]["commit"]
                if upstream == locked:
                    lines.append(f"  ✓ {item['name']}: locked revision is current")
                else:
                    lines.append(f"  ! {item['name']}: update available {locked[:12]} -> {upstream[:12]}")
        except FleetError as exc:
            lines.append(f"  ! update check unavailable: {exc}")
    return lines, errors


def resolve_updates(paths: Paths, *, dry_run: bool = False) -> tuple[dict[str, Any], list[dict[str, str]]]:
    manifest = load_manifest(paths)
    current = load_lock(paths)
    expected_names = {item["name"] for item in manifest_items(manifest)}
    current_external = current.get("external", {})
    extra_names = set(current_external) - expected_names
    if extra_names:
        raise FleetError(f"lock contains entries absent from manifest: {', '.join(sorted(extra_names))}")
    candidate = {"version": 1, "external": {}}
    for item in manifest_items(manifest):
        existing = current_external.get(item["name"])
        if existing is not None:
            if not isinstance(existing, dict) or existing.get("repo") != item["repo"] or existing.get("path") != item["path"]:
                raise FleetError(f"lock entry {item['name']} does not match manifest")
            candidate["external"][item["name"]] = json.loads(json.dumps(existing))
        else:
            candidate["external"][item["name"]] = {"repo": item["repo"], "path": item["path"]}
    updates: list[dict[str, str]] = []
    by_repo: dict[str, str] = {}
    for item in manifest_items(manifest):
        repo_url = item["repo"]
        if repo_url not in by_repo:
            if dry_run:
                branch = str((item.get("track") or {}).get("branch", "main"))
                result = _run(["git", "ls-remote", repo_url, f"refs/heads/{branch}"], check=False)
                if result.returncode != 0 or not (result.stdout or "").strip():
                    raise FleetError(f"could not resolve upstream {repo_url} branch {branch}")
                by_repo[repo_url] = (result.stdout or "").split()[0]
            else:
                cached = ensure_repo_cache(paths, repo_url)
                by_repo[repo_url] = tracked_revision(cached, item.get("track"))
        new_commit = by_repo[repo_url]
        old_commit = candidate["external"][item["name"]].get("commit")
        if new_commit != old_commit:
            candidate["external"][item["name"]]["commit"] = new_commit
            updates.append({"name": item["name"], "repo": repo_url, "old": old_commit or "(new)", "new": new_commit})
    return candidate, updates


def diff_locks(paths: Paths, old_path: Path, new_path: Path) -> list[str]:
    old, new = _read_yaml(old_path), _read_yaml(new_path)
    old_items, new_items = old.get("external", {}), new.get("external", {})
    lines: list[str] = []
    for name in sorted(set(old_items) | set(new_items)):
        before, after = old_items.get(name), new_items.get(name)
        if before == after:
            continue
        lines.append(f"{name}: {before.get('commit', '(none)') if before else '(none)'} -> {after.get('commit', '(none)') if after else '(none)'}")
        if not before or not after or before.get("repo") != after.get("repo"):
            continue
        repo = cached_repo(paths, after["repo"])
        if not repo.exists():
            lines.append("  repository is not cached; run bootstrap or fetch it before reviewing file changes")
            continue
        old_commit, new_commit = before.get("commit"), after.get("commit")
        path = after["path"]
        changed = _run(["git", "-C", str(repo), "diff", "--name-status", old_commit, new_commit, "--", path], check=False)
        files = [line for line in (changed.stdout or "").splitlines() if line.strip()]
        lines.append(f"  path: {path}")
        lines.append(f"  changed files: {len(files)}")
        for file_line in files:
            lines.append(f"    {file_line}")
        detail = _run(["git", "-C", str(repo), "diff", "--stat", old_commit, new_commit, "--", path], check=False)
        for line in (detail.stdout or "").splitlines():
            lines.append(f"    {line}")
        for file_line in files:
            changed_path = file_line.split("\t", 1)[-1]
            if changed_path.endswith("SKILL.md"):
                lines.append("  ! SKILL.md changed")
            if "/scripts/" in f"/{changed_path}" or changed_path.startswith(f"{path}/scripts/"):
                lines.append("  ! executable/script area changed")
            if file_line.startswith("A\t") and ("/bin/" in f"/{changed_path}" or "/scripts/" in f"/{changed_path}"):
                lines.append("  ! new script/binary appeared")
        summary = _run(["git", "-C", str(repo), "diff", "--summary", old_commit, new_commit, "--", path], check=False)
        for line in (summary.stdout or "").splitlines():
            if "mode change" in line or "create mode" in line:
                lines.append(f"  ! executable mode change: {line.strip()}")
    return lines


def run_native_commands(manifest: Mapping[str, Any], *, operation: str, allow: bool) -> None:
    commands: list[tuple[str, str, str]] = []
    for item in manifest_items(manifest):
        for agent, config in (item.get("native") or {}).items():
            command = config.get(operation) if isinstance(config, dict) else None
            if command:
                commands.append((item["name"], agent, command))
    if not commands:
        return
    print("Native operations declared:")
    for name, agent, command in commands:
        print(f"  {name} [{agent}] {operation}: {command}")
    if not allow:
        print("Native commands were not run. Re-run with --allow-native after reviewing them.", file=sys.stderr)
        return
    for name, agent, command in commands:
        print(f"Running reviewed native command for {name} [{agent}]...")
        _run(["/bin/sh", "-c", command], capture=False)
