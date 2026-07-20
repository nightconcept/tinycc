#!/bin/sh
set -eu

zig=${ZIG:-zig}
case "$(uname -s)" in
  Darwin)
    platform=macos-arm64
    cc="$zig cc"
    zig_flags=
    ;;
  Linux)
    platform=linux-x64
    cc="$zig cc"
    zig_flags=
    ;;
  *)
    echo "unsupported build host: $(uname -s)" >&2
    exit 1
    ;;
esac

make distclean >/dev/null 2>&1 || true
./src/configure --prefix=/ --cc="$cc"
make -j2
make test-mtcc ZIG="$zig" MTCC_ZIG_FLAGS="$zig_flags"
make test CC=/usr/bin/cc
make test-relocate-macos

mkdir -p dist
cp mtcc "dist/mtcc-$platform"
