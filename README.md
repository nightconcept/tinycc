# MTCC (Modern Tiny C Compiler)

MTCC is a Zig-built, single-file frontend around a vendored copy of
[TinyCC](https://bellard.org/tcc/). The unmodified-as-possible TinyCC
sources, build system, and docs live in `src/`; everything at the repo
root is MTCC-specific.

## Quick start

```sh
mise install
just hooks-install
just build
./build/mtcc hello.c
```

## Usage

Run a C file directly:

```sh
mtcc hello.c
```

Or route to an explicit subcommand:

```sh
mtcc run <file.c>     # compile and run
mtcc build <file.c>   # compile to an executable
mtcc lint <file.c>    # static checks, no build
mtcc tcc [args...]    # pass args straight through to TinyCC
```

## Development

All dev tasks go through `just` (see `justfile`):

```sh
just build           # out-of-tree configure+build into build/
just test-legacy     # vendored upstream TinyCC test suite
just test-toolchain  # mtcc CLI tests (not compilation)
just test            # both, legacy first
just package         # copy build/mtcc into dist/
just gate-fast       # fmt + zig unit tests (pre-commit)
just gate            # gate-fast + build + full test suite (pre-push)
```

## License

The mtcc project is licensed under the [`LGPL-2.1 LICENSE`](LICENSE).
