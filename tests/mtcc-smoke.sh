#!/bin/sh
set -eu

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT HUP INT TERM
repo=$PWD
export MTCC_CACHE_DIR="$tmp/cache"

cp ./mtcc "$tmp/mtcc"
cd "$tmp"

[ "$(./mtcc "$repo/src/examples/ex1.c")" = "Hello World" ]
[ "$(./mtcc run "$repo/src/tests/tests2/31_args.c" -- one two | tail -1)" = "arg 2: two" ]

./mtcc build "$repo/src/examples/ex1.c" -o "$tmp/hello"
[ "$("$tmp/hello")" = "Hello World" ]

./mtcc lint "$repo/src/examples/ex1.c"
if ./mtcc lint -Dtest_invalid_1 "$repo/src/tests/tests2/60_errors_and_warnings.c" 2>/dev/null; then
    echo "mtcc lint accepted invalid C" >&2
    exit 1
fi

./mtcc tcc -v >/dev/null
test -f "$MTCC_CACHE_DIR/include/stddef.h"
test -f "$MTCC_CACHE_DIR/libtcc1.a"
