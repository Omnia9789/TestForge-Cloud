"""
core/coverage.py — Generates a static HTML coverage report from pytest-cov output.

Usage (from project root):
    python -m core.coverage

This runs pytest with coverage on the core/ package, then opens the HTML report.
No extra gigabytes — pytest-cov is a small package (~200 KB).

The report is saved to: coverage_report/index.html
"""

import subprocess
import sys
import webbrowser
from pathlib import Path


REPORT_DIR = Path("coverage_report")


def run_coverage_report(open_browser: bool = True) -> int:
    """
    Runs pytest with coverage collection and generates an HTML report.

    Returns:
        Exit code (0 = success, non-zero = failures)
    """
    print("Running pytest with coverage...\n")

    result = subprocess.run(
        [
            sys.executable, "-m", "pytest",
            "tests/",
            "--cov=core",
            f"--cov-report=html:{REPORT_DIR}",
            "--cov-report=term-missing",
            "-v",
        ],
        capture_output=False,
    )

    if result.returncode == 0:
        report_path = REPORT_DIR / "index.html"
        print(f"\nCoverage report generated: {report_path.resolve()}")

        if open_browser:
            print("Opening in browser...")
            webbrowser.open(report_path.resolve().as_uri())
    else:
        print("\nSome tests failed. Coverage report still generated if any tests ran.")

    return result.returncode


if __name__ == "__main__":
    sys.exit(run_coverage_report(open_browser=True))
