#!/usr/bin/env python3
"""Unified build/test/package entrypoint for MTCC.

Replaces scripts/build-mtcc.sh, win32/build-mtcc.ps1, win32/test-mtcc.ps1,
tests/mtcc-smoke.sh and tests/relocate-macos.sh with a single, platform-
dispatching CLI. Windows still has no `make`, so it drives zig/build-tcc.bat
directly; POSIX drives everything through the vendored Makefile.

All build output (objects, libs, tcc, mtcc) lands in build/ via an
out-of-tree configure, keeping the repo root and src/ clean. Packaged
release artifacts go in dist/ (also gitignored).
"""
import argparse
import os
import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BUILD_DIR = ROOT / "build"
DIST_DIR = ROOT / "dist"
ZIG = os.environ.get("ZIG", "zig")
IS_WINDOWS = sys.platform == "win32"
EXE = ".exe" if IS_WINDOWS else ""


def run(cmd, **kw):
    kw.setdefault("cwd", ROOT)
    print("+", " ".join(str(c) for c in cmd), flush=True)
    subprocess.run(cmd, check=True, **kw)


def artifact_name():
    if IS_WINDOWS:
        return "mtcc-windows-x64.exe"
    system = platform.system()
    if system == "Darwin":
        return "mtcc-macos-arm64"
    if system == "Linux":
        return "mtcc-linux-x64"
    sys.exit(f"unsupported build host: {system}")


# --------------------------------------------------------------------------
# build


def build_posix():
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)
    BUILD_DIR.mkdir(parents=True)
    run(["../src/configure", "--prefix=/", f"--cc={ZIG} cc"], cwd=BUILD_DIR)
    run(["make", "-j2"], cwd=BUILD_DIR)
    run(["make", "mtcc", f"ZIG={ZIG}", f"MTCC_ZIG_SRC={ROOT / 'mtcc.zig'}"], cwd=BUILD_DIR)


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

    stage = Path(tempfile.mkdtemp(prefix="mtcc-runtime-"))
    try:
        (stage / "include").mkdir(parents=True)
        (stage / "lib").mkdir(parents=True)
        for item in (src_win32 / "include").iterdir():
            dest = stage / "include" / item.name
            shutil.copytree(item, dest) if item.is_dir() else shutil.copy(item, dest)
        for item in (src_win32 / "lib").iterdir():
            dest = stage / "lib" / item.name
            shutil.copytree(item, dest) if item.is_dir() else shutil.copy(item, dest)
        run(["tar", "-cf", str(BUILD_DIR / "mtcc-runtime.tar"), "-C", str(stage), "."])
    finally:
        shutil.rmtree(stage, ignore_errors=True)

    run(
        [ZIG, "cc", "-O2", "-c", str(ROOT / "src" / "tcc.c"), "-I" + str(ROOT), "-o", "mtcc-tcc.obj",
         "-DTCC_MAIN=tcc_main", "-DTCC_TARGET_PE", "-DTCC_TARGET_X86_64"],
        cwd=BUILD_DIR,
    )
    run(
        [ZIG, "build-exe", "-O", "ReleaseSafe", "-femit-bin=mtcc.exe",
         str(ROOT / "mtcc.zig"), "mtcc-tcc.obj", "-lc"],
        cwd=BUILD_DIR,
    )


def cmd_build(args):
    build_windows() if IS_WINDOWS else build_posix()


# --------------------------------------------------------------------------
# test: legacy (vendored upstream TinyCC suite)


def test_legacy_posix(args):
    run(["make", "test", f"CC={args.cc}"], cwd=BUILD_DIR)


def test_legacy_windows(args):
    run(["cmd", "/c", "test-win32.bat", "all", "-k"], cwd=ROOT / "src" / "tests")


def cmd_test_legacy(args):
    test_legacy_windows(args) if IS_WINDOWS else test_legacy_posix(args)


# --------------------------------------------------------------------------
# test: toolchain (mtcc CLI behavior, not upstream compilation correctness)


def zig_unit_tests():
    run([ZIG, "test", str(ROOT / "mtcc.zig"), "-lc"])


def smoke_test():
    mtcc_bin = BUILD_DIR / f"mtcc{EXE}"
    tmp = Path(tempfile.mkdtemp(prefix="mtcc-smoke-"))
    try:
        cache = tmp / "cache"
        env = os.environ.copy()
        env["MTCC_CACHE_DIR"] = str(cache)
        local_mtcc = tmp / mtcc_bin.name
        shutil.copy(mtcc_bin, local_mtcc)
        local_mtcc.chmod(0o755)

        ex1 = ROOT / "src" / "examples" / "ex1.c"
        args_c = ROOT / "src" / "tests" / "tests2" / "31_args.c"
        errors_c = ROOT / "src" / "tests" / "tests2" / "60_errors_and_warnings.c"

        def mtcc(*a, **kw):
            kw.setdefault("cwd", tmp)
            kw.setdefault("env", env)
            return subprocess.run([str(local_mtcc), *a], **kw)

        out = mtcc(str(ex1), capture_output=True, text=True, check=True).stdout.strip()
        assert out == "Hello World", f"run failed: {out!r}"

        out = mtcc("run", str(args_c), "--", "one", "two", capture_output=True, text=True, check=True).stdout
        assert out.strip().splitlines()[-1] == "arg 2: two", "args test failed"

        hello = tmp / f"hello{EXE}"
        mtcc("build", str(ex1), "-o", str(hello), check=True)
        out = subprocess.run([str(hello)], capture_output=True, text=True, check=True).stdout.strip()
        assert out == "Hello World", "build failed"

        mtcc("lint", str(ex1), check=True)

        result = mtcc("lint", "-Dtest_invalid_1", str(errors_c), capture_output=True)
        if result.returncode == 0:
            sys.exit("mtcc lint accepted invalid C")

        mtcc("tcc", "-v", capture_output=True, check=True)

        assert (cache / "include" / "stddef.h").exists(), "headers not extracted"
        libtcc1 = cache / "lib" / "libtcc1.a" if IS_WINDOWS else cache / "libtcc1.a"
        assert libtcc1.exists(), "runtime not extracted"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def relocate_macos_test():
    if platform.system() != "Darwin":
        return
    tmp = Path(tempfile.mkdtemp(prefix="mtcc-relocate-"))
    try:
        installed = tmp / "installed"
        run(["make", "install", f"DESTDIR={installed}"], cwd=BUILD_DIR, stdout=subprocess.DEVNULL)
        relocated = tmp / "relocated"
        installed.rename(relocated)
        env = os.environ.copy()
        env.pop("SDKROOT", None)
        hello = tmp / "hello"
        run(
            [str(relocated / "bin" / "tcc"), f"-B{relocated / 'lib' / 'tcc'}",
             str(ROOT / "src" / "examples" / "ex1.c"), "-o", str(hello)],
            env=env,
        )
        out = subprocess.run([str(hello)], capture_output=True, text=True, check=True).stdout.strip()
        assert out == "Hello World", "relocated tcc failed"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def cmd_test_toolchain(args):
    zig_unit_tests()
    smoke_test()
    relocate_macos_test()


# --------------------------------------------------------------------------
# test: all (legacy gate first, then toolchain)


def cmd_test_all(args):
    cmd_test_legacy(args)
    cmd_test_toolchain(args)


# --------------------------------------------------------------------------
# package


def cmd_package(args):
    DIST_DIR.mkdir(exist_ok=True)
    shutil.copy(BUILD_DIR / f"mtcc{EXE}", DIST_DIR / artifact_name())


# --------------------------------------------------------------------------
# ci: full pipeline used by GitHub Actions


def cmd_ci(args):
    cmd_build(args)
    cmd_test_all(args)
    cmd_package(args)


# --------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("build", help="configure and build mtcc into build/").set_defaults(func=cmd_build)

    p_test = sub.add_parser("test", help="run tests").add_subparsers(dest="test_target", required=True)
    p_legacy = p_test.add_parser("legacy", help="run the vendored upstream TinyCC suite")
    p_legacy.add_argument("--cc", default="/usr/bin/cc", help="system compiler used by the legacy suite")
    p_legacy.set_defaults(func=cmd_test_legacy)
    p_test.add_parser("toolchain", help="run mtcc CLI/toolchain tests").set_defaults(func=cmd_test_toolchain)
    p_all = p_test.add_parser("all", help="legacy suite, then toolchain tests")
    p_all.add_argument("--cc", default="/usr/bin/cc", help="system compiler used by the legacy suite")
    p_all.set_defaults(func=cmd_test_all)

    sub.add_parser("package", help="copy the built binary into dist/").set_defaults(func=cmd_package)

    p_ci = sub.add_parser("ci", help="build, test all, package")
    p_ci.add_argument("--cc", default="/usr/bin/cc", help="system compiler used by the legacy suite")
    p_ci.set_defaults(func=cmd_ci)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
