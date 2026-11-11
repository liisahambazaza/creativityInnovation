"""Run every check, in order, and say plainly what passed and what failed.

python scripts/check.py          everything, including the browser tests
python scripts/check.py --fast   skip the browser tests (used by the git hook)
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY = sys.executable


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--fast", action="store_true", help="skip the browser tests")
    args = parser.parse_args()

    steps = [
        ("Code style (ruff)", [PY, "-m", "ruff", "check", "."]),
        ("Code formatting (ruff format)", [PY, "-m", "ruff", "format", "--check", "."]),
        ("Corpus audit", [PY, "-m", "kanjian.corpus"]),
        ("Tests", [PY, "-m", "pytest", "-q", *(["-m", "not browser"] if args.fast else [])]),
    ]

    results = []
    for name, command in steps:
        print(f"\n=== {name} ===", flush=True)
        started = time.monotonic()
        code = subprocess.call(command, cwd=ROOT)
        results.append((name, code == 0, time.monotonic() - started))

    print("\n=== Summary ===")
    for name, ok, seconds in results:
        print(f"  {'pass' if ok else 'FAIL'}  {name}  ({seconds:.1f}s)")
    if args.fast:
        print("  skip  Browser tests (run without --fast to include them)")
    failed = [name for name, ok, _ in results if not ok]
    print("\nAll checks passed." if not failed else f"\n{len(failed)} check(s) failed: {', '.join(failed)}.")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
