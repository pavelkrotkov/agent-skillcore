import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml

from agent_skillfleet.core import Paths, assemble_runtime


class RuntimeCheckoutIndependenceTests(unittest.TestCase):
    def test_active_first_party_runtime_survives_whole_checkout_move(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            repo = base / "checkout"
            skill = repo / "skills" / "github-project-swarm"
            skill.mkdir(parents=True)
            (skill / "SKILL.md").write_text(
                "---\nname: github-project-swarm\ndescription: checkout independence test\n---\n",
                encoding="utf-8",
            )
            (repo / "external").mkdir()
            (repo / "overrides").mkdir()
            (repo / "external" / "skills.yaml").write_text(
                yaml.safe_dump({"version": 1, "external": []}), encoding="utf-8"
            )
            (repo / "external" / "skills.lock").write_text(
                yaml.safe_dump({"version": 1, "external": {}}), encoding="utf-8"
            )
            subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True)
            subprocess.run(["git", "config", "user.email", "tests@example.invalid"], cwd=repo, check=True)
            subprocess.run(["git", "config", "user.name", "Skillfleet Tests"], cwd=repo, check=True)
            subprocess.run(["git", "add", "."], cwd=repo, check=True)
            subprocess.run(["git", "commit", "-m", "initial"], cwd=repo, check=True, capture_output=True)
            paths = Paths(repo, base / "runtime", base / "cache", base / "state")
            assemble_runtime(paths, activate=True)
            deployed = paths.active_runtime / "github-project-swarm" / "SKILL.md"
            expected = deployed.read_text(encoding="utf-8")
            repo.rename(base / "checkout-moved")
            self.assertEqual(expected, deployed.read_text(encoding="utf-8"))
            self.assertFalse((paths.active_runtime / "github-project-swarm").is_symlink())


if __name__ == "__main__":
    unittest.main()
