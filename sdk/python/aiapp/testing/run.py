"""Runs an app's tests (used by `aiapp test`): unittest discovery in tests/,
or pytest when it is installed and --pytest is given."""

from __future__ import annotations

import argparse
import os
import sys
import unittest


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="aiapp test")
    p.add_argument("-k", dest="pattern", default=None, help="only tests whose names contain this")
    p.add_argument("--pytest", action="store_true", help="run with pytest instead of unittest")
    p.add_argument("-v", "--verbose", action="store_true")
    p.add_argument("dir", nargs="?", default="tests")
    a = p.parse_args(argv)
    if not os.path.isdir(a.dir):
        print(f"no {a.dir}/ folder: add tests like tests/test_app.py (see `aiapp new` templates)", file=sys.stderr)
        return 5
    sys.path.insert(0, os.getcwd())
    if a.pytest:
        import pytest  # noqa: PLC0415

        args = [a.dir, "-q", "-p", "aiapp.testing.pytest_plugin"] + (["-k", a.pattern] if a.pattern else []) + (["-v"] if a.verbose else [])
        return int(pytest.main(args))
    loader = unittest.TestLoader()
    if a.pattern:
        loader.testNamePatterns = [f"*{a.pattern}*"]
    suite = loader.discover(a.dir, pattern="test*.py", top_level_dir=os.path.abspath(a.dir))  # no __init__.py needed
    if suite.countTestCases() == 0:
        print(f"no tests found in {a.dir}/", file=sys.stderr)
        return 5
    result = unittest.TextTestRunner(verbosity=2 if a.verbose else 1).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
