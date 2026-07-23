#!/usr/bin/env python3
"""Configure and build ztcc into build/.

Windows has no `make`, so it drives zig/build-tcc.bat directly; POSIX
drives everything through the vendored Makefile. All build output
(objects, libs, tcc, ztcc) lands in build/ via an out-of-tree configure,
keeping the repo root and src/ clean.
"""
import os
import shutil
import tempfile
from pathlib import Path

from common import BUILD_DIR, IS_WINDOWS, ROOT, ZIG, run


def build_posix():
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)
    BUILD_DIR.mkdir(parents=True)
    run(["../src/configure", "--prefix=/", f"--cc={ZIG} cc"], cwd=BUILD_DIR)
    run(["make", "-j2"], cwd=BUILD_DIR)
    run(["make", "ztcc", f"ZIG={ZIG}", f"ZTCC_ZIG_SRC={ROOT / 'ztcc.zig'}"], cwd=BUILD_DIR)


def build_windows():
    src_win32 = ROOT / "src" / "win32"
    BUILD_DIR.mkdir(exist_ok=True)

    env = os.environ.copy()
    env["TCC_C"] = "..\\tcc.c"
    run(["cmd", "/c", "build-tcc.bat", "-clean"], cwd=src_win32, env=env)
    run(["cmd", "/c", "build-tcc.bat", "-c", f"{ZIG} cc -O2", "-t", "x86_64"], cwd=src_win32, env=env)
    run(
        [ZIG, "cc", "-O2", "-shared", "../libtcc.c", "-I..", "-o", "libtcc.dll",
         "-DTCC_TARGET_PE", "-DTCC_TARGET_X86_64", "-DLIBTCC_AS_DLL"],
        cwd=src_win32,
    )

    stage = Path(tempfile.mkdtemp(prefix="ztcc-runtime-"))
    try:
        (stage / "include").mkdir(parents=True)
        (stage / "lib").mkdir(parents=True)
        for item in (src_win32 / "include").iterdir():
            dest = stage / "include" / item.name
            shutil.copytree(item, dest) if item.is_dir() else shutil.copy(item, dest)
        for item in (src_win32 / "lib").iterdir():
            dest = stage / "lib" / item.name
            shutil.copytree(item, dest) if item.is_dir() else shutil.copy(item, dest)
        run(["tar", "-cf", str(BUILD_DIR / "ztcc-runtime.tar"), "-C", str(stage), "."])
    finally:
        shutil.rmtree(stage, ignore_errors=True)

    run(
        [ZIG, "cc", "-O2", "-c", str(ROOT / "src" / "tcc.c"), "-I" + str(ROOT), "-o", "ztcc-tcc.obj",
         "-DTCC_MAIN=tcc_main", "-DTCC_TARGET_PE", "-DTCC_TARGET_X86_64"],
        cwd=BUILD_DIR,
    )
    run(
        [ZIG, "build-exe", "-O", "ReleaseSafe", "-femit-bin=ztcc.exe",
         str(ROOT / "ztcc.zig"), "ztcc-tcc.obj", "-lc"],
        cwd=BUILD_DIR,
    )


def main():
    build_windows() if IS_WINDOWS else build_posix()


if __name__ == "__main__":
    main()
