#!/usr/bin/env python3
"""Full pipeline used by GitHub Actions: build, test (legacy then toolchain), package."""
import argparse
import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cc", default="/usr/bin/cc", help="system compiler used by the legacy suite")
    args = parser.parse_args()

    python = sys.executable
    subprocess.run([python, str(SCRIPTS / "build.py")], check=True)
    subprocess.run([python, str(SCRIPTS / "test_legacy.py"), "--cc", args.cc], check=True)
    subprocess.run([python, str(SCRIPTS / "test_toolchain.py")], check=True)
    subprocess.run([python, str(SCRIPTS / "package.py")], check=True)


if __name__ == "__main__":
    main()
