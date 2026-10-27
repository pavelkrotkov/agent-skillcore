from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

from agent_skillfleet.core import (
    FleetError,
    Paths,
    activate_runtime,
    assemble_runtime,
    cached_repo,
    doctor,
    first_party_skills,
    install_links,
    load_manifest,
    resolve_updates,
    validate_manifest_lock,
    validate_runtime,
)


SKILL = """---
name: {name}
description: A deterministic test skill used by Skillfleet integration tests.
---

# {name}

Follow the test instructions.
"""


class SkillfleetIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="skillfleet-test-")
        self.root = Path(self.temp.name) / "fleet"
        self.root.mkdir()
        (self.root / "skills" / "skillfleet-example").mkdir(parents=True)
        (self.root / "skills" / "skillfleet-example" / "SKILL.md").write_text(
            SKILL.format(name="skillfleet-example"), encoding="utf-8"
        )
        (self.root / "external").mkdir()
        (self.root / "overrides").mkdir()
        self.upstream = Path(self.temp.name) / "upstream"
        self._git("init", "-b", "main", cwd=self.upstream, create=True)
        self._git("config", "user.email", "tests@example.invalid", cwd=self.upstream)
        self._git("config", "user.name", "Skillfleet Tests", cwd=self.upstream)
        skill = self.upstream / "skills" / "vendor-skill"
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text(SKILL.format(name="vendor-skill"), encoding="utf-8")
        self._git("add", ".", cwd=self.upstream)
        self._git("commit", "-m", "initial skill", cwd=self.upstream)
        self.commit = self._git("rev-parse", "HEAD", cwd=self.upstream).strip()
        self.repo_url = self.upstream.as_uri()
        self._write_dependency_files()
        self._git("init", "-b", "main", cwd=self.root)
        self._git("config", "user.email", "tests@example.invalid", cwd=self.root)
        self._git("config", "user.name", "Skillfleet Tests", cwd=self.root)
        self._git("add", ".", cwd=self.root)
        self._git("commit", "-m", "test checkout", cwd=self.root)
        self.paths = Paths(
            repo=self.root,
            runtime=Path(self.temp.name) / "runtime",
            cache=Path(self.temp.name) / "cache",
            state=Path(self.temp.name) / "state",
        )

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _git(self, *args: str, cwd: Path, create: bool = False) -> str:
        if create:
            cwd.mkdir(parents=True, exist_ok=True)
        result = subprocess.run(
            ["git", *args], cwd=cwd, text=True, capture_output=True, check=True
        )
        return result.stdout

    def _write_dependency_files(self, *, name: str = "vendor-skill", path: str = "skills/vendor-skill", commit: str | None = None) -> None:
        manifest = {
            "version": 1,
            "external": [
                {
                    "name": name,
                    "repo": self.repo_url,
                    "path": path,
                    "track": {"branch": "main"},
                    "deployment": {"codex": "shared", "claude": "shared", "hermes": "shared"},
                }
            ],
        }
        lock = {
            "version": 1,
            "external": {
                name: {"repo": self.repo_url, "path": path, "commit": commit or self.commit}
            },
        }
        (self.root / "external" / "skills.yaml").write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")
        (self.root / "external" / "skills.lock").write_text(yaml.safe_dump(lock, sort_keys=False), encoding="utf-8")

    def _env(self) -> dict[str, str]:
        return {
            "AGENT_SKILLFLEET_CODEX_DIR": str(Path(self.temp.name) / "codex"),
            "AGENT_SKILLFLEET_CLAUDE_DIR": str(Path(self.temp.name) / "claude"),
        }

    def test_malformed_manifest_and_duplicate_names_are_rejected(self) -> None:
        (self.root / "external" / "skills.yaml").write_text("version: 1\nexternal: nope\n", encoding="utf-8")
        with self.assertRaises(FleetError):
            load_manifest(self.paths)
        self._write_dependency_files()
        manifest = yaml.safe_load((self.root / "external" / "skills.yaml").read_text())
        manifest["external"].append(dict(manifest["external"][0]))
        (self.root / "external" / "skills.yaml").write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")
        with self.assertRaises(FleetError):
            load_manifest(self.paths)

    def test_lock_rejects_invalid_commit_and_manifest_disagreement(self) -> None:
        self._write_dependency_files(commit="not-a-sha")
        with self.assertRaises(FleetError):
            validate_manifest_lock(self.paths)
        self._write_dependency_files(commit=self.commit)
        lock = yaml.safe_load((self.root / "external" / "skills.lock").read_text())
        lock["external"]["vendor-skill"]["path"] = "skills/other"
        (self.root / "external" / "skills.lock").write_text(yaml.safe_dump(lock, sort_keys=False), encoding="utf-8")
        with self.assertRaises(FleetError):
            validate_manifest_lock(self.paths)

    def test_assemble_validates_shared_cache_and_writes_provenance(self) -> None:
        release = assemble_runtime(self.paths, activate=False)
        self.assertTrue(release.is_dir())
        self.assertEqual({"skillfleet-example", "vendor-skill"}, {name for name, _ in first_party_skills(self.paths)} | {"vendor-skill"})
        first_party = release / "skillfleet-example"
        self.assertTrue((first_party / "SKILL.md").is_file())
        self.assertFalse(first_party.is_symlink())
        self.assertTrue((release / "vendor-skill" / "SKILL.md").is_file())
        metadata = release / ".skillfleet-meta"
        self.assertEqual("first-party", json.loads((metadata / "skillfleet-example.json").read_text())["kind"])
        self.assertEqual("external", json.loads((metadata / "vendor-skill.json").read_text())["kind"])
        activate_runtime(self.paths.runtime, release)
        messages = validate_runtime(self.paths)
        self.assertIn("2 skills validated", messages)
        self.assertTrue(cached_repo(self.paths, self.repo_url).is_dir())

    def test_first_party_snapshot_survives_checkout_skill_move(self) -> None:
        release = assemble_runtime(self.paths, activate=True)
        deployed = self.paths.active_runtime / "skillfleet-example" / "SKILL.md"
        expected = deployed.read_text(encoding="utf-8")
        source = self.root / "skills" / "skillfleet-example"
        source.rename(self.root / "skills" / "skillfleet-example.moved")
        self.assertEqual(release.resolve(), self.paths.active_runtime.resolve())
        self.assertEqual(expected, deployed.read_text(encoding="utf-8"))

    def test_first_party_upgrade_switches_only_when_candidate_is_activated(self) -> None:
        first = assemble_runtime(self.paths, activate=True)
        active_skill = self.paths.active_runtime / "skillfleet-example" / "SKILL.md"
        self.assertNotIn("Second release", active_skill.read_text(encoding="utf-8"))
        source = self.root / "skills" / "skillfleet-example" / "SKILL.md"
        source.write_text(source.read_text(encoding="utf-8") + "\nSecond release.\n", encoding="utf-8")
        self._git("add", "skills/skillfleet-example/SKILL.md", cwd=self.root)
        self._git("commit", "-m", "second first-party release", cwd=self.root)
        second = assemble_runtime(self.paths, activate=False)
        self.assertNotEqual(first, second)
        self.assertEqual(first.resolve(), self.paths.active_runtime.resolve())
        self.assertNotIn("Second release", active_skill.read_text(encoding="utf-8"))
        activate_runtime(self.paths.runtime, second)
        self.assertEqual(second.resolve(), self.paths.active_runtime.resolve())
        self.assertIn("Second release", active_skill.read_text(encoding="utf-8"))

    def test_first_party_external_name_collision_is_rejected(self) -> None:
        self._write_dependency_files(name="skillfleet-example", path="skills/vendor-skill")
        with self.assertRaisesRegex(FleetError, "collision"):
            assemble_runtime(self.paths)

    def test_patch_failure_stops_before_activation(self) -> None:
        self.paths.overrides.mkdir(exist_ok=True)
        override = self.paths.overrides / "vendor-skill"
        override.mkdir()
        (override / "series").write_text("0001-does-not-apply.patch\n", encoding="utf-8")
        (override / "0001-does-not-apply.patch").write_text(
            "diff --git a/SKILL.md b/SKILL.md\n--- a/SKILL.md\n+++ b/SKILL.md\n@@ -1 +1 @@\n-this line is absent\n+replacement\n",
            encoding="utf-8",
        )
        with self.assertRaises(FleetError):
            assemble_runtime(self.paths)
        self.assertFalse(self.paths.active_runtime.exists())

    def test_managed_links_cleanup_preserves_unrelated_links_and_dry_run(self) -> None:
        release = assemble_runtime(self.paths, activate=False)
        activate_runtime(self.paths.runtime, release)
        with patch.dict(os.environ, self._env(), clear=False):
            dry_messages = install_links(self.paths, dry_run=True)
            self.assertTrue(any(message.startswith("would") for message in dry_messages))
            self.assertFalse((Path(self.temp.name) / "codex").exists())
            install_links(self.paths)
            manual_target = Path(self.temp.name) / "manual"
            manual_target.mkdir()
            manual_link = Path(self.temp.name) / "codex" / "manual"
            manual_link.symlink_to(manual_target, target_is_directory=True)
            new_release = Path(self.temp.name) / "new-release"
            new_release.mkdir()
            (new_release / ".skillfleet-meta").mkdir()
            (new_release / "skillfleet-example").symlink_to((self.root / "skills" / "skillfleet-example").resolve(), target_is_directory=True)
            activate_runtime(self.paths.runtime, new_release)
            messages = install_links(self.paths)
            self.assertTrue(any("removed vendor-skill" in message for message in messages))
            self.assertTrue(manual_link.is_symlink())
            self.assertFalse((Path(self.temp.name) / "codex" / "vendor-skill").exists())

    def test_candidate_failure_does_not_replace_current_runtime(self) -> None:
        release = assemble_runtime(self.paths, activate=False)
        activate_runtime(self.paths.runtime, release)
        current_target = self.paths.active_runtime.resolve()
        self._write_dependency_files(commit="0" * 40)
        with self.assertRaises(FleetError):
            candidate = assemble_runtime(self.paths, runtime=Path(self.temp.name) / "candidate", activate=False)
            validate_runtime(self.paths, candidate)
        self.assertEqual(current_target, self.paths.active_runtime.resolve())

    def test_update_resolution_is_deterministic_and_groups_shared_repository(self) -> None:
        old = self.commit
        (self.upstream / "skills" / "vendor-skill" / "SKILL.md").write_text(SKILL.format(name="vendor-skill") + "\nUpdated.\n", encoding="utf-8")
        self._git("add", ".", cwd=self.upstream)
        self._git("commit", "-m", "update skill", cwd=self.upstream)
        new = self._git("rev-parse", "HEAD", cwd=self.upstream).strip()
        candidate, updates = resolve_updates(self.paths, dry_run=True)
        self.assertEqual(new, candidate["external"]["vendor-skill"]["commit"])
        self.assertEqual(1, len(updates))
        self.assertNotEqual(old, new)

    def test_update_resolution_adds_a_new_manifest_entry_to_the_candidate_lock(self) -> None:
        manifest = yaml.safe_load((self.root / "external" / "skills.yaml").read_text())
        manifest["external"].append(
            {
                "name": "vendor-second",
                "repo": self.repo_url,
                "path": "skills/vendor-skill",
                "track": {"branch": "main"},
                "deployment": {"codex": "shared", "claude": "shared", "hermes": "shared"},
            }
        )
        (self.root / "external" / "skills.yaml").write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")
        candidate, updates = resolve_updates(self.paths, dry_run=True)
        self.assertIn("vendor-second", candidate["external"])
        self.assertEqual(self.commit, candidate["external"]["vendor-second"]["commit"])
        self.assertEqual("(new)", next(update["old"] for update in updates if update["name"] == "vendor-second"))

    def test_doctor_reports_an_upstream_update_when_cache_is_refreshable(self) -> None:
        release = assemble_runtime(self.paths, activate=False)
        activate_runtime(self.paths.runtime, release)
        (self.upstream / "skills" / "vendor-skill" / "SKILL.md").write_text(SKILL.format(name="vendor-skill") + "\nDoctor update.\n", encoding="utf-8")
        self._git("add", ".", cwd=self.upstream)
        self._git("commit", "-m", "doctor update", cwd=self.upstream)
        lines, errors = doctor(self.paths, fetch=True)
        self.assertEqual(0, errors)
        self.assertTrue(any("update available" in line for line in lines))

    def test_dirty_checkout_refuses_sync_before_remote_operations(self) -> None:
        (self.root / "dirty.txt").write_text("uncommitted\n", encoding="utf-8")
        env = os.environ | {
            "AGENT_SKILLFLEET_RUNTIME": str(self.paths.runtime),
            "AGENT_SKILLFLEET_CACHE": str(self.paths.cache),
            "AGENT_SKILLFLEET_STATE": str(self.paths.state),
        }
        result = subprocess.run(
            [sys.executable, str(Path(__file__).parents[1] / "src/agent_skillfleet/cli.py"), "--repo", str(self.root), "sync"],
            text=True,
            capture_output=True,
            env=env,
            check=False,
        )
        self.assertEqual(1, result.returncode)
        self.assertIn("dirty", result.stderr)


if __name__ == "__main__":
    unittest.main()
