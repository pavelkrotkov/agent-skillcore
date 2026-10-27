"""Prevent private companion material from entering public commits."""
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = {"amazon-aliexpress-research", "email-cleanup", "github-repo-maintenance",
          "hermes-cleanup", "skillfleet-example", "travel-orchestrator",
          "volleyball-video-analysis", "x-curator", "zoom-call-archive"}


class PublicBoundaryTests(unittest.TestCase):
    def test_only_public_first_party_skills_and_no_migration_state_are_tracked(self):
        files = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).decode().split("\0")
        skills = {p.split("/")[1] for p in files if p.startswith("skills/") and p.endswith("/SKILL.md")}
        self.assertEqual(skills, PUBLIC)
        for name in files:
            self.assertFalse(name.startswith((".migration/", "runtime/", ".env")), name)
            self.assertNotIn("family-defaults.md", name)

    def test_public_workflows_do_not_request_companion_or_provider_secrets(self):
        for path in (ROOT / ".github/workflows").glob("*.yml"):
            text = path.read_text()
            self.assertNotIn("secrets.", text, path.name)
            self.assertNotIn("agent-skillfleet.git", text, path.name)
