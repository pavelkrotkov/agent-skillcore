from pathlib import Path
import unittest

from radon.complexity import cc_visit
from radon.metrics import mi_visit


class XQualityTests(unittest.TestCase):
    def test_fresh_runtime_meets_operator_quality_gates(self):
        root = Path(__file__).resolve().parents[1]
        paths = list((root / "skills/x-curator/scripts/x_curator").glob("*.py"))
        paths.extend((root / "skills/x-curator/scripts").glob("repair*.py"))
        paths.append(root / "skills/x-curator/scripts/x-repair-qualify.py")
        paths.extend((root / "tests").glob("test_x_*.py"))
        paths.extend((root / "tests").glob("x_*.py"))
        for path in paths:
            with self.subTest(path=str(path.relative_to(root))):
                source = path.read_text()
                self.assertGreater(mi_visit(source, multi=False), 50)
                for block in cc_visit(source):
                    self.assertLess(block.complexity, 8, block.name)


if __name__ == "__main__":
    unittest.main()
