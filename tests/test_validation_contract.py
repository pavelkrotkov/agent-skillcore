import contextlib
import io
import os
from pathlib import Path
import sys
import unittest
from unittest import mock

import yaml

ROOT = Path(__file__).parents[1]
TOOLS = ROOT / "tools"
SRC = ROOT / "src"
for path in (str(TOOLS), str(SRC)):
    if path not in sys.path:
        sys.path.insert(0, path)

from agent_skillfleet.core import FleetError, Paths, validate_skill_dir
from agent_skillfleet.validation import validate_reference, validate_source
import ci_validate


class ValidationDomainTests(unittest.TestCase):
    def test_source_validation_never_consults_skills_ref_on_path(self):
        paths = Paths.from_environment(ROOT)
        with mock.patch("agent_skillfleet.core.shutil.which", side_effect=AssertionError("PATH consulted")):
            messages = validate_source(paths)
        self.assertTrue(messages)

    def test_core_skill_validation_defaults_to_offline(self):
        skill = ROOT / "skills" / "skillfleet-example"
        with mock.patch("agent_skillfleet.core.shutil.which", side_effect=AssertionError("PATH consulted")):
            self.assertEqual(validate_skill_dir(skill), [])

    def test_reference_validation_is_explicit_and_requires_tool(self):
        with mock.patch("agent_skillfleet.validation.shutil.which", return_value=None):
            with self.assertRaisesRegex(FleetError, "explicit reference validation"):
                validate_reference(Paths.from_environment(ROOT))

    def test_cli_defaults_to_source_and_has_separate_modes(self):
        from agent_skillfleet.cli import make_parser
        parser = make_parser()
        default = parser.parse_args(["validate"])
        runtime = parser.parse_args(["validate", "--runtime"])
        reference = parser.parse_args(["validate", "--reference"])
        self.assertFalse(default.runtime or default.reference)
        self.assertTrue(runtime.runtime)
        self.assertTrue(reference.reference)


class CanonicalEntrypointTests(unittest.TestCase):
    def test_independent_failures_are_aggregated_and_labeled(self):
        checks = [
            ci_validate.Check("Unit tests", lambda: 3),
            ci_validate.Check("Source and manifest validation", lambda: 7),
            ci_validate.Check("Independent success", lambda: 0),
        ]
        output = io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            status = ci_validate.run_checks(checks)
        text = output.getvalue()
        self.assertEqual(status, 1)
        self.assertIn("[FAIL] Unit tests", text)
        self.assertIn("[FAIL] Source and manifest validation", text)
        self.assertIn("[PASS] Independent success", text)

    def test_command_env_overlay_preserves_parent_environment(self):
        code = (
            "import os,sys; "
            "sys.exit(0 if os.environ.get('CI_PARENT_MARKER') == 'parent' "
            "and os.environ.get('CI_CHILD_MARKER') == 'child' and os.environ.get('PATH') else 1)"
        )
        with mock.patch.dict(os.environ, {"CI_PARENT_MARKER": "parent"}, clear=False):
            status = ci_validate._command([sys.executable, "-c", code], env={"CI_CHILD_MARKER": "child"})()
        self.assertEqual(status, 0)

    def test_workflow_has_one_post_setup_validation_command(self):
        workflow = (ROOT / ".github/workflows/validate.yml").read_text(encoding="utf-8")
        self.assertIn("python-version: '3.12'", workflow)
        self.assertEqual(workflow.count("run: make check"), 1)
        for old in ("bin/skill-validate --manifest-only", "bash -n bin/*", "git grep -n"):
            self.assertNotIn(old, workflow)

    def test_make_validate_is_full_gate_and_test_remains_narrow(self):
        makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
        self.assertIn("check:\n\tAGENT_SKILLFLEET_PYTHON=", makefile)
        self.assertIn("validate: check", makefile)
        self.assertIn("test:\n\t$(PYTHON) -m unittest", makefile)
        self.assertNotIn("qualify-swarm", makefile)

    def test_ci_dependency_stack_is_pinned(self):
        constraints = (ROOT / "requirements/ci-constraints.txt").read_text(encoding="utf-8")
        for requirement in ("PyYAML==6.0.3", "radon==6.0.1", "mando==0.7.1", "colorama==0.4.6", "six==1.17.0"):
            self.assertIn(requirement, constraints)

    def test_swarm_quality_is_owned_by_public_dependency(self):
        checks = {check.label for check in ci_validate.build_checks()}
        self.assertNotIn("Swarm quality policy", checks)
        self.assertNotIn("Dead-code boundary", checks)
        lock = yaml.safe_load((ROOT / "external" / "skills.lock").read_text(encoding="utf-8"))
        roles = ("github-project-swarm", "github-project-reviewer", "github-project-adjudicator")
        revisions = set()
        for role in roles:
            entry = lock["external"][role]
            self.assertEqual(entry["repo"], "https://github.com/pavelkrotkov/gh-swarm.git")
            self.assertEqual(entry["path"], "skills/" + role)
            self.assertRegex(entry["commit"], r"\A[0-9a-f]{40}\Z")
            revisions.add(entry["commit"])
        self.assertEqual(len(revisions), 1)


if __name__ == "__main__":
    unittest.main()
