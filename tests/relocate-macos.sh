#!/bin/sh
set -eu

[ "$(uname -s)" = Darwin ] || exit 0

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT HUP INT TERM

make install DESTDIR="$tmp/installed" >/dev/null
mv "$tmp/installed" "$tmp/relocated"
env -u SDKROOT "$tmp/relocated/bin/tcc" \
    -B"$tmp/relocated/lib/tcc" \
    "$PWD/examples/ex1.c" -o "$tmp/hello"
[ "$("$tmp/hello")" = "Hello World" ]
