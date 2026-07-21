#!/usr/bin/env python3
"""End-to-end benchmark runner comparing the MIR/c2mir backend (this clone)
against the current TinyCC backend (main repo), with gcc/clang as an
optional native-compile reference ceiling.

Two suites:
  1. Synthetic build-time stress test: compile ~300 varied .c files
     (bench/synthetic/, see gen_synthetic.py) with each available compiler,
     -c only (no link). Reports batch total, per-file average, peak RSS.
  2. Interpreted/JIT micro-benchmarks (bench/micro/*.c): fib, mandelbrot,
     sieve, quicksort. For c2m: JIT (-eg, build+run combined), and AOT
     (separate -c build step + a standalone run via mir-bin-run, when that
     helper builds successfully). For tcc: JIT (-run) and AOT (compile+link,
     then execute, timed separately). For gcc/clang (if present): AOT -O2
     compile then execute, timed separately.

No third-party dependencies -- stdlib only. Safe to re-run repeatedly;
synthetic/ is regenerated deterministically and tmp_obj/ is scratch space
that gets overwritten each run.

tcc is used as the baseline for ratio columns, since the point of this spike
is "should mc replace tcc with MIR/c2mir".
"""
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

BENCH_DIR = Path(__file__).resolve().parent
CLONE_ROOT = BENCH_DIR.parent
MAIN_REPO_ROOT = CLONE_ROOT.parent

SYNTHETIC_DIR = BENCH_DIR / "synthetic"
MICRO_DIR = BENCH_DIR / "micro"
TMP_DIR = BENCH_DIR / "tmp_obj"
BIN_DIR = BENCH_DIR / "bin"
RESULTS_DIR = BENCH_DIR / "results"

TIME_L = ["/usr/bin/time", "-l"]


# --------------------------------------------------------------------------
# compiler discovery


def discover_compilers():
    compilers = {}

    c2m = CLONE_ROOT / "build" / "c2m"
    if c2m.exists():
        compilers["c2m"] = {"path": c2m}
    else:
        warn("clone/build/c2m not found -- run `cd clone && python3 scripts/dev.py build`")

    tcc = MAIN_REPO_ROOT / "build" / "tcc"
    tcc_build_dir = MAIN_REPO_ROOT / "build"
    if tcc.exists():
        compilers["tcc"] = {"path": tcc, "build_dir": tcc_build_dir}
    else:
        warn("main repo build/tcc not found -- skipping tcc comparison arm")

    for name in ("gcc", "clang"):
        found = shutil.which(name)
        if found:
            compilers[name] = {"path": Path(found)}
        else:
            warn("%s not found on PATH -- skipping" % name)

    return compilers


def warn(msg):
    print("WARNING: %s" % msg, file=sys.stderr)


def ensure_mir_bin_run(compilers):
    """Build MIR's standalone .bmir runner (src/mir-bin-run.c) if missing, so
    the c2m AOT path has a real "run only" number distinct from "build only".
    Best-effort: on failure, just skip AOT-run timing for c2m and note it."""
    if "c2m" not in compilers:
        return None
    exe = BIN_DIR / "mir-bin-run"
    if exe.exists():
        return exe
    BIN_DIR.mkdir(parents=True, exist_ok=True)
    zig = os.environ.get("ZIG", "zig")
    obj = BIN_DIR / "mir-bin-run.o"
    src_dir = CLONE_ROOT / "src"
    libmir = CLONE_ROOT / "build" / "libmir.a"
    try:
        subprocess.run(
            [zig, "cc", "-c", str(src_dir / "mir-bin-run.c"), "-o", str(obj),
             "-I", str(src_dir), "-I", str(src_dir / "c2mir"), "-O2"],
            check=True, capture_output=True,
        )
        subprocess.run(
            [zig, "cc", str(obj), str(libmir), "-o", str(exe), "-lpthread"],
            check=True, capture_output=True,
        )
        return exe
    except subprocess.CalledProcessError as e:
        warn("could not build mir-bin-run (%s) -- c2m AOT run time will be "
             "reported as build+run combined only" % e)
        return None


# --------------------------------------------------------------------------
# timed subprocess execution


def run_timed(cmd, cwd=None, env=None):
    """Run cmd wrapped in `/usr/bin/time -l`. Returns dict with wall seconds
    (measured in Python around the whole invocation), peak RSS in bytes (as
    reported by `time -l`'s "maximum resident set size"), returncode, and
    captured stdout/stderr (with the `time -l` report stripped off stderr)."""
    full = TIME_L + [str(c) for c in cmd]
    t0 = time.perf_counter()
    proc = subprocess.run(full, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    wall = time.perf_counter() - t0
    stderr_text = proc.stderr.decode(errors="replace")
    maxrss = None
    body_lines = []
    for line in stderr_text.splitlines():
        s = line.strip()
        if s.endswith("maximum resident set size"):
            try:
                maxrss = int(s.split()[0])
            except ValueError:
                pass
        elif s.endswith("real") and " user " in s:
            pass  # time's own (coarse) wall clock; we use perf_counter instead
        elif any(s.endswith(suf) for suf in (
            "average shared memory size", "average unshared data size",
            "average unshared stack size", "page reclaims", "page faults",
            "swaps", "block input operations", "block output operations",
            "messages sent", "messages received", "signals received",
            "voluntary context switches", "involuntary context switches",
            "instructions retired", "cycles elapsed", "peak memory footprint",
        )):
            pass
        else:
            body_lines.append(line)
    return {
        "wall": wall,
        "maxrss": maxrss,
        "returncode": proc.returncode,
        "stdout": proc.stdout.decode(errors="replace"),
        "stderr": "\n".join(body_lines),
    }


# --------------------------------------------------------------------------
# suite 1: synthetic build-time stress test


def synthetic_compile_cmd(name, info, src, out):
    if name == "c2m":
        return [info["path"], "-c", src, "-o", out]
    if name == "tcc":
        return [info["path"], "-c", src, "-o", out]
    if name in ("gcc", "clang"):
        return [info["path"], "-c", src, "-o", out]
    raise ValueError(name)


def run_synthetic_suite(compilers):
    files = sorted(SYNTHETIC_DIR.glob("*.c"))
    if not files:
        warn("no synthetic files found -- run gen_synthetic.py first")
        return {}
    TMP_DIR.mkdir(parents=True, exist_ok=True)

    results = {}
    for name, info in compilers.items():
        out_ext = ".bmir" if name == "c2m" else ".o"
        per_file = []
        peak_rss = 0
        failures = 0
        t_start = time.perf_counter()
        for f in files:
            out = TMP_DIR / (f.stem + out_ext)
            cmd = synthetic_compile_cmd(name, info, f, out)
            r = run_timed(cmd)
            if r["returncode"] != 0:
                failures += 1
                continue
            per_file.append(r["wall"])
            if r["maxrss"]:
                peak_rss = max(peak_rss, r["maxrss"])
        batch_total = time.perf_counter() - t_start
        results[name] = {
            "files": len(files),
            "failures": failures,
            "batch_total_sec": batch_total,
            "avg_per_file_sec": sum(per_file) / len(per_file) if per_file else None,
            "peak_rss_bytes": peak_rss,
        }
        print("  [synthetic] %-6s batch=%.3fs avg/file=%.4fs peak_rss=%.1fMB failures=%d" % (
            name, batch_total, results[name]["avg_per_file_sec"] or -1,
            peak_rss / 1e6, failures,
        ))
    return results


# --------------------------------------------------------------------------
# suite 2: micro benchmarks


def run_c2m_micro(info, src, mir_bin_run):
    out = {}
    # Combined JIT: build+run in one process, not separable.
    out["jit_combined"] = run_timed([info["path"], src, "-eg"])
    # AOT: build step alone.
    bmir = TMP_DIR / (src.stem + ".bmir")
    out["aot_build"] = run_timed([info["path"], "-c", src, "-o", bmir])
    # AOT: run step alone, if we have a standalone runner.
    if mir_bin_run is not None and out["aot_build"]["returncode"] == 0:
        out["aot_run"] = run_timed([mir_bin_run, bmir, bmir.name])
    else:
        out["aot_run"] = None
    return out


def run_tcc_micro(info, src):
    out = {}
    out["jit_combined"] = run_timed(
        [info["path"], "-B", info["build_dir"], "-run", src]
    )
    binf = TMP_DIR / (src.stem + ".tccbin")
    out["aot_build"] = run_timed(
        [info["path"], "-B", info["build_dir"], src, "-o", binf]
    )
    if out["aot_build"]["returncode"] == 0:
        out["aot_run"] = run_timed([binf])
    else:
        out["aot_run"] = None
    return out


def run_native_micro(info, src):
    out = {}
    binf = TMP_DIR / (src.stem + "." + info["path"].name + ".bin")
    out["aot_build"] = run_timed([info["path"], "-O2", src, "-o", binf])
    if out["aot_build"]["returncode"] == 0:
        out["aot_run"] = run_timed([binf])
    else:
        out["aot_run"] = None
    out["jit_combined"] = None  # no JIT mode for gcc/clang
    return out


def run_micro_suite(compilers, mir_bin_run):
    files = sorted(MICRO_DIR.glob("*.c"))
    results = {}
    for f in files:
        bench_name = f.stem
        results[bench_name] = {}
        for name, info in compilers.items():
            if name == "c2m":
                r = run_c2m_micro(info, f, mir_bin_run)
            elif name == "tcc":
                r = run_tcc_micro(info, f)
            else:
                r = run_native_micro(info, f)
            results[bench_name][name] = r
            jit = r["jit_combined"]["wall"] if r["jit_combined"] else None
            build = r["aot_build"]["wall"] if r["aot_build"] else None
            run_ = r["aot_run"]["wall"] if r["aot_run"] else None
            print("  [micro] %-12s %-6s jit=%s build=%s run=%s" % (
                bench_name, name,
                "%.3fs" % jit if jit is not None else "n/a",
                "%.4fs" % build if build is not None else "n/a",
                "%.4fs" % run_ if run_ is not None else "n/a",
            ))
    return results


# --------------------------------------------------------------------------
# reporting


def fmt_sec(v):
    return "%.4f" % v if v is not None else "n/a"


def fmt_mb(v):
    return "%.1f" % (v / 1e6) if v else "n/a"


def fmt_ratio(v, base):
    if v is None or base is None or base == 0:
        return "n/a"
    return "%.2fx" % (v / base)


def build_report_text(synthetic, micro):
    lines = []
    lines.append("# mc backend benchmark: MIR/c2mir vs TinyCC")
    lines.append("")
    lines.append("Baseline for ratio columns: **tcc** (current mc backend).")
    lines.append("")
    lines.append("## 1. Synthetic build-time stress test (%d files, -c only)" %
                  (next(iter(synthetic.values()))["files"] if synthetic else 0))
    lines.append("")
    lines.append("| compiler | batch total (s) | avg/file (s) | peak RSS (MB) | vs tcc (batch) | failures |")
    lines.append("|---|---|---|---|---|---|")
    base_batch = synthetic.get("tcc", {}).get("batch_total_sec")
    for name in ("c2m", "tcc", "gcc", "clang"):
        if name not in synthetic:
            continue
        d = synthetic[name]
        lines.append("| %s | %.3f | %s | %s | %s | %d |" % (
            name, d["batch_total_sec"], fmt_sec(d["avg_per_file_sec"]),
            fmt_mb(d["peak_rss_bytes"]), fmt_ratio(d["batch_total_sec"], base_batch),
            d["failures"],
        ))
    lines.append("")

    lines.append("## 2. Interpreted/JIT micro-benchmarks")
    lines.append("")
    lines.append("`jit` = single-shot build+run combined (c2m `-eg`, tcc `-run`). "
                  "`build` / `run` = ahead-of-time compile step and standalone execution, timed separately "
                  "(c2m via `-c` then `mir-bin-run`; tcc/gcc/clang via compile-to-binary then execute).")
    lines.append("")
    for bench_name, per_compiler in micro.items():
        lines.append("### %s" % bench_name)
        lines.append("")
        lines.append("| compiler | jit (s) | build (s) | run (s) | build+run vs tcc jit | peak RSS build (MB) | peak RSS run (MB) |")
        lines.append("|---|---|---|---|---|---|---|")
        base_jit = None
        if "tcc" in per_compiler and per_compiler["tcc"]["jit_combined"]:
            base_jit = per_compiler["tcc"]["jit_combined"]["wall"]
        for name in ("c2m", "tcc", "gcc", "clang"):
            if name not in per_compiler:
                continue
            r = per_compiler[name]
            jit = r["jit_combined"]["wall"] if r["jit_combined"] else None
            build = r["aot_build"]["wall"] if r["aot_build"] else None
            run_ = r["aot_run"]["wall"] if r["aot_run"] else None
            build_plus_run = (build or 0) + (run_ or 0) if (build is not None and run_ is not None) else None
            compare = jit if jit is not None else build_plus_run
            rss_build = r["aot_build"]["maxrss"] if r["aot_build"] else None
            rss_run = r["aot_run"]["maxrss"] if r["aot_run"] else None
            lines.append("| %s | %s | %s | %s | %s | %s | %s |" % (
                name, fmt_sec(jit), fmt_sec(build), fmt_sec(run_),
                fmt_ratio(compare, base_jit), fmt_mb(rss_build), fmt_mb(rss_run),
            ))
        lines.append("")
    return "\n".join(lines)


def build_report_json(synthetic, micro):
    def strip(r):
        if r is None:
            return None
        return {"wall": r["wall"], "maxrss": r["maxrss"], "returncode": r["returncode"]}

    micro_json = {}
    for bench_name, per_compiler in micro.items():
        micro_json[bench_name] = {}
        for name, r in per_compiler.items():
            micro_json[bench_name][name] = {
                "jit_combined": strip(r["jit_combined"]),
                "aot_build": strip(r["aot_build"]),
                "aot_run": strip(r["aot_run"]),
            }
    return {"synthetic": synthetic, "micro": micro_json}


def main():
    print("== mc backend benchmark (MIR/c2mir vs TinyCC) ==")
    print("clone root: %s" % CLONE_ROOT)
    print("main repo:  %s" % MAIN_REPO_ROOT)
    print()

    compilers = discover_compilers()
    print("compilers under test: %s" % ", ".join(sorted(compilers)))
    print()

    if not SYNTHETIC_DIR.exists() or not any(SYNTHETIC_DIR.glob("*.c")):
        print("generating synthetic corpus...")
        sys.path.insert(0, str(BENCH_DIR))
        import gen_synthetic
        gen_synthetic.generate()
        print()

    mir_bin_run = ensure_mir_bin_run(compilers)
    if "c2m" in compilers and mir_bin_run is None:
        warn("proceeding without mir-bin-run; c2m AOT 'run' column will be n/a")

    print("--- suite 1: synthetic build-time stress test ---")
    synthetic = run_synthetic_suite(compilers)
    print()

    print("--- suite 2: micro-benchmarks ---")
    micro = run_micro_suite(compilers, mir_bin_run)
    print()

    report_text = build_report_text(synthetic, micro)
    print(report_text)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    (RESULTS_DIR / "report.md").write_text(report_text)
    (RESULTS_DIR / "report.json").write_text(json.dumps(build_report_json(synthetic, micro), indent=2))
    print()
    print("wrote %s and %s" % (RESULTS_DIR / "report.md", RESULTS_DIR / "report.json"))


if __name__ == "__main__":
    main()
