#!/usr/bin/env python3
"""Canonical hermetic source-validation entrypoint used locally and by CI."""
from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Callable, Iterable

import yaml

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from agent_skillfleet.core import SECRET_PATTERNS  # noqa: E402


@dataclass(frozen=True)
class Check:
    label: str
    action: Callable[[], int]


def _tracked_files(root: Path = ROOT) -> list[Path]:
    proc = subprocess.run(
        ["git", "ls-files", "-z"], cwd=root, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False
    )
    if proc.returncode:
        detail = proc.stderr.decode(errors="replace").strip()
        raise RuntimeError(f"git ls-files failed: {detail}")
    return [root / raw.decode("utf-8") for raw in proc.stdout.split(b"\0") if raw]


def _command(args: list[str], *, env: dict[str, str] | None = None) -> Callable[[], int]:
    def run() -> int:
        merged_env = os.environ.copy()
        if env is not None:
            merged_env.update(env)
        proc = subprocess.run(args, cwd=ROOT, env=merged_env, check=False)
        return proc.returncode

    return run


def _yaml_check() -> int:
    failures: list[str] = []
    for path in _tracked_files():
        if path.suffix.lower() not in {".yaml", ".yml"}:
            continue
        try:
            yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
            failures.append(f"{path.relative_to(ROOT)}: {exc}")
    for failure in failures:
        print(f"  - {failure}", file=sys.stderr)
    return 1 if failures else 0


def _shell_check() -> int:
    if shutil.which("bash") is None:
        print("  - required tool 'bash' is unavailable", file=sys.stderr)
        return 1
    failures: list[str] = []
    for path in _tracked_files():
        relative = path.relative_to(ROOT)
        is_bin = relative.parts and relative.parts[0] == "bin"
        if not (is_bin or path.suffix == ".sh"):
            continue
        try:
            first = path.read_text(encoding="utf-8").splitlines()[0]
        except (OSError, UnicodeDecodeError, IndexError):
            continue
        if "bash" not in first:
            continue
        proc = subprocess.run(["bash", "-n", str(path)], cwd=ROOT, text=True, capture_output=True, check=False)
        if proc.returncode:
            failures.append(f"{relative}: {(proc.stderr or proc.stdout).strip()}")
    for failure in failures:
        print(f"  - {failure}", file=sys.stderr)
    return 1 if failures else 0


def _secret_check() -> int:
    failures: list[str] = []
    for path in _tracked_files():
        relative = path.relative_to(ROOT)
        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if any(pattern.search(content) for pattern in SECRET_PATTERNS):
            failures.append(str(relative))
    for failure in failures:
        print(f"  - possible secret material: {failure}", file=sys.stderr)
    return 1 if failures else 0


def build_checks() -> list[Check]:
    validation_env = {"AGENT_SKILLFLEET_PYTHON": sys.executable}
    return [
        Check("YAML parse", _yaml_check),
        Check("Unit tests", _command([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py", "-v"])),
        Check("Source and manifest validation", _command([str(ROOT / "bin" / "skill-validate"), "--manifest-only"], env=validation_env)),
        Check("Shell syntax policy", _shell_check),
        Check("Tracked-source secret scan", _secret_check),
    ]


def run_checks(checks: Iterable[Check]) -> int:
    failures: list[str] = []
    for check in checks:
        print(f"\n=== {check.label} ===", flush=True)
        try:
            status = int(check.action())
        except Exception as exc:
            status = 1
            print(f"  - check crashed: {exc}", file=sys.stderr)
        if status:
            failures.append(check.label)
            print(f"[FAIL] {check.label} (exit {status})", file=sys.stderr, flush=True)
        else:
            print(f"[PASS] {check.label}", flush=True)
    print("\n=== Validation summary ===")
    if failures:
        print(f"{len(failures)} validation domain(s) failed:", file=sys.stderr)
        for label in failures:
            print(f"  - {label}", file=sys.stderr)
        return 1
    print("all validation domains passed")
    return 0


def main() -> int:
    return run_checks(build_checks())


if __name__ == "__main__":
    raise SystemExit(main())
