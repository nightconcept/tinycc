# MTC plan

MTC (Modern Tiny C Compiler) stays a thin layer on TinyCC's `mob` branch.
Keep TCC changes small enough that `dev` can be rebased directly onto
`upstream/mob`.

## 1. Fix relocatable macOS SDK lookup

- Resolve `SDKROOT` at runtime, falling back to
  `xcrun --sdk macosx --show-sdk-path`.
- Add `<SDK>/usr/include` as a system include path and `<SDK>/usr/lib` as a
  library path.
- Remove the build machine's SDK path from packaged binaries.
- Add one smoke check that compiles and runs a program using `<stdio.h>` after
  relocating the package.

## 2. Add the Zig frontend

- Build TCC with `zig cc`; keep TCC's existing configure/Make build.
- Add a small `mtc` entry point that routes commands into embedded TCC.
- Make `mtc hello.c` equivalent to running that source with TCC.
- Preserve the original interface under `mtc tcc ...`.

Initial commands:

```text
mtc hello.c
mtc run hello.c -- [args]
mtc build hello.c -o hello
mtc lint hello.c
mtc tcc [tcc arguments]
```

## 3. Ship native artifacts

- Produce one artifact per supported OS and architecture.
- Embed TCC's private headers, helper objects, and `libtcc1.a` in `mtc`; unpack
  them into a versioned cache on first use.
- Require only operating-system libraries at runtime. On macOS, require an
  installed SDK for programs using macOS headers and libraries.

Start with macOS arm64, Linux x86_64, and Windows x86_64. Add other targets
only after their smoke checks pass.

## 4. Add tooling without growing a second compiler

- Implement `mtc lint` with TCC's existing diagnostics first.
- Do not write a C formatter. Add `mtc fmt` only when a formatter can be
  embedded or delegated without obscuring its dependency.

## Branches and remotes

- `upstream/mob`: canonical TinyCC base.
- `origin/mtc`: MTC development, rebased onto `upstream/mob`.
- `origin/release-builds`: existing GitHub nightly builder; leave it isolated
  from MTC development.
