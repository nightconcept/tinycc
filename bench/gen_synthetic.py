#!/usr/bin/env python3
"""Generate a batch of syntactically varied but small C source files used as
a build-time stress test (compile ~N files, measure batch + per-file time and
peak memory for each compiler under test).

Deterministic (no RNG) so repeated runs produce byte-identical output --
regenerate any time with `python3 gen_synthetic.py`. Output lands in
synthetic/ which is not meant to be committed (see bench/.gitignore).

Four file "flavors" are cycled by index:
  0: plain arithmetic functions
  1: local arrays + structs
  2: loop-heavy functions
  3: many small functions (parse/codegen breadth)
"""
import os
from pathlib import Path

OUT_DIR = Path(__file__).resolve().parent / "synthetic"
N_FILES = 300


def arithmetic_file(idx):
    lines = ["/* synthetic: arithmetic */", "int base_%d(int x) { return x; }" % idx]
    for i in range(12):
        lines.append(
            "int f%d_%d(int a, int b) { "
            "int c = a * %d + b - %d; "
            "int d = (c ^ %d) & 0xff; "
            "return c + d - base_%d(a); }" % (idx, i, i + 1, i * 2 + 1, i + 3, idx)
        )
    lines.append("int main(void) {")
    lines.append("    int acc = 0;")
    for i in range(12):
        lines.append("    acc += f%d_%d(%d, %d);" % (idx, i, i, i * 3))
    lines.append("    return acc & 0xff;")
    lines.append("}")
    return "\n".join(lines) + "\n"


def array_struct_file(idx):
    lines = [
        "/* synthetic: arrays + structs */",
        "struct point_%d { int x; int y; int tag; };" % idx,
        "struct rect_%d { struct point_%d tl; struct point_%d br; };" % (idx, idx, idx),
        "",
        "static int area_%d(struct rect_%d r) {" % (idx, idx),
        "    int w = r.br.x - r.tl.x;",
        "    int h = r.br.y - r.tl.y;",
        "    return w * h;",
        "}",
        "",
        "int build_%d(int seed) {" % idx,
        "    struct point_%d pts[16];" % idx,
        "    int sums[16];",
        "    int i;",
        "    for (i = 0; i < 16; i++) {",
        "        pts[i].x = seed + i;",
        "        pts[i].y = seed - i;",
        "        pts[i].tag = i % 4;",
        "    }",
        "    for (i = 0; i < 16; i++) {",
        "        sums[i] = pts[i].x * pts[i].y + pts[i].tag;",
        "    }",
        "    {",
        "        struct rect_%d r;" % idx,
        "        r.tl = pts[0];",
        "        r.br = pts[15];",
        "        return area_%d(r) + sums[7];" % idx,
        "    }",
        "}",
        "",
        "int main(void) {",
        "    int total = 0;",
        "    int k;",
        "    for (k = 0; k < 8; k++) total += build_%d(k * 5);" % idx,
        "    return total & 0xff;",
        "}",
    ]
    return "\n".join(lines) + "\n"


def loop_file(idx):
    lines = [
        "/* synthetic: loop heavy */",
        "long sum_grid_%d(int n) {" % idx,
        "    long total = 0;",
        "    int i, j;",
        "    for (i = 0; i < n; i++) {",
        "        for (j = 0; j < n; j++) {",
        "            int v = (i * 31 + j * 17) % 97;",
        "            if (v % 2 == 0) {",
        "                total += v;",
        "            } else {",
        "                total -= v / 2;",
        "            }",
        "        }",
        "    }",
        "    return total;",
        "}",
        "",
        "int fib_iter_%d(int n) {" % idx,
        "    int a = 0, b = 1, i;",
        "    for (i = 0; i < n; i++) {",
        "        int t = a + b;",
        "        a = b;",
        "        b = t;",
        "    }",
        "    return a;",
        "}",
        "",
        "int main(void) {",
        "    long s = sum_grid_%d(20);" % idx,
        "    int f = fib_iter_%d(20);" % idx,
        "    return (int)((s + f) & 0xff);",
        "}",
    ]
    return "\n".join(lines) + "\n"


def many_functions_file(idx):
    lines = ["/* synthetic: many small functions */"]
    n = 60
    for i in range(n):
        lines.append("int tiny_%d_%d(int x) { return x * %d + %d; }" % (idx, i, i + 1, i))
    lines.append("int main(void) {")
    lines.append("    int acc = 0;")
    for i in range(n):
        lines.append("    acc = tiny_%d_%d(acc);" % (idx, i))
    lines.append("    return acc & 0xff;")
    lines.append("}")
    return "\n".join(lines) + "\n"


FLAVORS = [arithmetic_file, array_struct_file, loop_file, many_functions_file]


def generate():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    # Clear stale files so a shrink in N_FILES doesn't leave orphans.
    for f in OUT_DIR.glob("*.c"):
        f.unlink()
    for i in range(N_FILES):
        flavor = FLAVORS[i % len(FLAVORS)]
        text = flavor(i)
        name = "%s_%03d.c" % (flavor.__name__.replace("_file", ""), i)
        (OUT_DIR / name).write_text(text)
    print("generated %d files in %s" % (N_FILES, OUT_DIR))


if __name__ == "__main__":
    generate()
