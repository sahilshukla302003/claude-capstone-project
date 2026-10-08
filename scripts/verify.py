"""Verification gate: default suite with coverage, mandatory slow suite, AC trace.

Usage: python scripts/verify.py
Writes only under output/test-results/. Exit code 0 only on a full pass.
"""

from __future__ import annotations

import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "output" / "test-results"
AC_IDS = tuple(f"AC-{n}" for n in range(1, 19))


def find_missing_acs(test_sources: str) -> list[str]:
    """AC ids that appear in no test name or docstring (case-insensitive)."""
    missing = []
    for ac in AC_IDS:
        number = ac.split("-")[1]
        pattern = rf"(?<![A-Za-z])ac[-_]?{number}(?!\d)"
        if re.search(pattern, test_sources, re.IGNORECASE) is None:
            missing.append(ac)
    return missing


def check_slow_results(junit_xml: str) -> list[str]:
    """Problems in the slow-suite junit report (empty list means it is fine)."""
    cases = list(ET.fromstring(junit_xml).iter("testcase"))
    if not cases:
        return ["no slow tests were executed"]
    problems = []
    skipped = [c.get("name", "?") for c in cases if c.find("skipped") is not None]
    if skipped:
        problems.append(f"slow tests skipped: {', '.join(skipped)}")
    failed = [c.get("name", "?") for c in cases
              if c.find("failure") is not None or c.find("error") is not None]
    if failed:
        problems.append(f"slow tests failed: {', '.join(failed)}")
    ran = [c.get("name", "") for c in cases if c.find("skipped") is None]
    if not any(re.search(r"ac_?16", name, re.IGNORECASE) for name in ran):
        problems.append("AC-16 did not run in the slow step")
    return problems


def _pytest(*args: str) -> int:
    cmd = [sys.executable, "-m", "pytest", *args]
    return subprocess.run(cmd, cwd=str(ROOT), check=False).returncode


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    problems: list[str] = []
    rc = _pytest("--cov=csv_summary", "--cov-report=term-missing",
                 "--cov-fail-under=90", "-q")
    if rc != 0:
        problems.append(f"default suite failed (exit {rc})")
    sources = "\n".join(p.read_text(encoding="utf-8")
                        for p in (ROOT / "tests").rglob("test_*.py"))
    missing = find_missing_acs(sources)
    if missing:
        problems.append(f"AC ids without a test: {', '.join(missing)}")
    junit = OUT_DIR / "slow.xml"
    junit.unlink(missing_ok=True)
    rc = _pytest("-m", "slow", "-s", "-q", f"--junitxml={junit}")
    if rc != 0:
        problems.append(f"slow suite failed (exit {rc})")
    if junit.exists():
        problems.extend(check_slow_results(junit.read_text(encoding="utf-8")))
    else:
        problems.append("slow suite produced no junit report")
    for problem in problems:
        print(f"VERIFY FAIL: {problem}", file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
