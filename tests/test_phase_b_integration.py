from pathlib import Path
import unittest

ROOT = Path(__file__).parents[1]


class ExternalQualityBoundaryTests(unittest.TestCase):
    def test_canonical_check_delegates_swarm_quality_to_public_dependency(self):
        makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
        ci_validate = (ROOT / "tools/ci_validate.py").read_text(encoding="utf-8")
        check_body = makefile.split("check:\n", 1)[1].split("\ntest:\n", 1)[0]

        self.assertIn("bash bin/ci-validate", check_body)
        self.assertNotIn("swarm_v7_quality.py", ci_validate)
        self.assertNotIn("swarm_v7_quality.py", makefile)
        self.assertNotIn("qualify-swarm", makefile)


if __name__ == "__main__":
    unittest.main()
