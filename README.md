# ZTCC (Zig Tiny C Compiler)

ZTCC is a Zig-built, single-file frontend around a vendored copy of
[TinyCC](https://bellard.org/tcc/). The unmodified-as-possible TinyCC
sources, build system, and docs live in `src/`; everything at the repo
root is ZTCC-specific.

## Quick start

```sh
mise install
just hooks-install
just build
./build/ztcc hello.c
```

## Usage

`ztcc` is a thin Zig wrapper around TinyCC: it bundles the runtime and
headers, then passes its arguments straight through to `tcc`.

```sh
ztcc -run hello.c     # compile and run
ztcc hello.c -o hello # compile to an executable
ztcc -v                # any other tcc argument works as-is
```

## Development

All dev tasks go through `just` (see `justfile`), each backed by a
single-purpose script in `scripts/`:

```sh
just build           # scripts/build.py — out-of-tree configure+build into build/
just test-legacy     # scripts/test_legacy.py — vendored upstream TinyCC test suite
just test-toolchain  # scripts/test_toolchain.py — ztcc CLI tests (not compilation)
just test            # both, legacy first
just package         # scripts/package.py — copy build/ztcc into dist/
just gate-fast       # fmt + zig unit tests (pre-commit)
just gate            # gate-fast + build + full test suite (pre-push)
```

## License

The ztcc project is licensed under the [`LGPL-2.1 LICENSE`](LICENSE).
