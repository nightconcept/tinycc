#!/usr/bin/env python3
"""Run the vendored upstream TinyCC test suite."""
import argparse

from common import BUILD_DIR, IS_WINDOWS, ROOT, run


def test_legacy_posix(cc):
    run(["make", "test", f"CC={cc}"], cwd=BUILD_DIR)


def test_legacy_windows():
    run(["cmd", "/c", "test-win32.bat", "all", "-k"], cwd=ROOT / "src" / "tests")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cc", default="/usr/bin/cc", help="system compiler used by the legacy suite")
    args = parser.parse_args()
    test_legacy_windows() if IS_WINDOWS else test_legacy_posix(args.cc)


if __name__ == "__main__":
    main()
