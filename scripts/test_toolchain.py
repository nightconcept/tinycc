#!/usr/bin/env python3
"""Run ztcc CLI/toolchain tests (not upstream compilation correctness)."""
import os
import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from common import BUILD_DIR, EXE, IS_WINDOWS, ROOT, ZIG, run


def zig_unit_tests():
    run([ZIG, "test", str(ROOT / "ztcc.zig"), "-lc"])


def smoke_test():
    ztcc_bin = BUILD_DIR / f"ztcc{EXE}"
    tmp = Path(tempfile.mkdtemp(prefix="ztcc-smoke-"))
    try:
        cache = tmp / "cache"
        env = os.environ.copy()
        env["ZTCC_CACHE_DIR"] = str(cache)
        local_ztcc = tmp / ztcc_bin.name
        shutil.copy(ztcc_bin, local_ztcc)
        local_ztcc.chmod(0o755)

        ex1 = ROOT / "src" / "examples" / "ex1.c"
        args_c = ROOT / "src" / "tests" / "tests2" / "31_args.c"
        errors_c = ROOT / "src" / "tests" / "tests2" / "60_errors_and_warnings.c"

        def ztcc(*a, **kw):
            kw.setdefault("cwd", tmp)
            kw.setdefault("env", env)
            return subprocess.run([str(local_ztcc), *a], **kw)

        out = ztcc("-run", str(ex1), capture_output=True, text=True, check=True).stdout.strip()
        assert out == "Hello World", f"run failed: {out!r}"

        out = ztcc("-run", str(args_c), "one", "two", capture_output=True, text=True, check=True).stdout
        assert out.strip().splitlines()[-1] == "arg 2: two", "args test failed"

        hello = tmp / f"hello{EXE}"
        ztcc(str(ex1), "-o", str(hello), check=True)
        out = subprocess.run([str(hello)], capture_output=True, text=True, check=True).stdout.strip()
        assert out == "Hello World", "build failed"

        result = ztcc("-c", "-Dtest_invalid_1", str(errors_c), "-o", str(tmp / "errors.o"), capture_output=True)
        if result.returncode == 0:
            sys.exit("ztcc accepted invalid C")

        ztcc("-v", capture_output=True, check=True)

        assert (cache / "include" / "stddef.h").exists(), "headers not extracted"
        libtcc1 = cache / "lib" / "libtcc1.a" if IS_WINDOWS else cache / "libtcc1.a"
        assert libtcc1.exists(), "runtime not extracted"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def relocate_macos_test():
    if platform.system() != "Darwin":
        return
    tmp = Path(tempfile.mkdtemp(prefix="ztcc-relocate-"))
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


def main():
    zig_unit_tests()
    smoke_test()
    relocate_macos_test()


if __name__ == "__main__":
    main()
