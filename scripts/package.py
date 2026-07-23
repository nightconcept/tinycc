#!/usr/bin/env python3
"""Copy the built ztcc binary into dist/."""
import platform
import shutil
import sys

from common import BUILD_DIR, DIST_DIR, EXE, IS_WINDOWS


def artifact_name():
    if IS_WINDOWS:
        return "ztcc-windows-x64.exe"
    system = platform.system()
    if system == "Darwin":
        return "ztcc-macos-arm64"
    if system == "Linux":
        return "ztcc-linux-x64"
    sys.exit(f"unsupported build host: {system}")


def main():
    DIST_DIR.mkdir(exist_ok=True)
    shutil.copy(BUILD_DIR / f"ztcc{EXE}", DIST_DIR / artifact_name())


if __name__ == "__main__":
    main()
