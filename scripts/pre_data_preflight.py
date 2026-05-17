"""Run pre-data baseline quality gates for the dashboard project."""

from __future__ import annotations

import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _run(cmd: list[str]) -> int:
    print(f"\n$ {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=ROOT)
    return result.returncode


def _scan_forbidden_patterns() -> int:
    forbidden = {
        "streamlit-deprecated-arg": re.compile(r"use_container_width\\s*=", re.IGNORECASE),
    }

    py_files = list((ROOT / "src" / "dashboard").rglob("*.py"))
    violations: list[str] = []

    for file in py_files:
        text = file.read_text(encoding="utf-8")
        for key, pattern in forbidden.items():
            if pattern.search(text):
                violations.append(f"{key}: {file.relative_to(ROOT)}")

    if violations:
        print("\nForbidden pattern check failed:")
        for item in violations:
            print(f"- {item}")
        return 1

    print("\nForbidden pattern check passed.")
    return 0


def main() -> int:
    print("Running pre-data baseline gates...")

    gates = [
        _run([sys.executable, "-m", "pytest", "-q"]),
        _run(
            [
                sys.executable,
                "-c",
                (
                    "import importlib; "
                    "mods=['src.dashboard.services.data_quality','src.dashboard.services.metrics',"
                    "'src.dashboard.services.data_source','src.dashboard.page_modules.executive_overview',"
                    "'src.dashboard.page_modules.match_review','src.dashboard.page_modules.matchups',"
                    "'src.dashboard.page_modules.opposition_report','src.dashboard.page_modules.batting_intelligence',"
                    "'src.dashboard.page_modules.bowling_intelligence']; "
                    "[importlib.import_module(m) for m in mods]; print('IMPORT_OK')"
                ),
            ]
        ),
        _scan_forbidden_patterns(),
    ]

    if any(code != 0 for code in gates):
        print("\nPre-data baseline gates failed.")
        return 1

    print("\nPre-data baseline gates passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
