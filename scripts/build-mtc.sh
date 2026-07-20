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
    cc="$zig cc -target native-linux-musl"
    zig_flags="-target native-linux-musl"
    ;;
  *)
    echo "unsupported build host: $(uname -s)" >&2
    exit 1
    ;;
esac

make distclean >/dev/null 2>&1 || true
./configure --prefix=/ --cc="$cc"
make -j2
make test-mtc ZIG="$zig" MTC_ZIG_FLAGS="$zig_flags"
make test CC=/usr/bin/cc
make test-relocate-macos

mkdir -p dist
cp mtc "dist/mtc-$platform"
