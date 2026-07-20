#!/bin/sh
set -eu

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT HUP INT TERM
repo=$PWD
export MTC_CACHE_DIR="$tmp/cache"

cp ./mtc "$tmp/mtc"
cd "$tmp"

[ "$(./mtc "$repo/examples/ex1.c")" = "Hello World" ]
[ "$(./mtc run "$repo/tests/tests2/31_args.c" -- one two | tail -1)" = "arg 2: two" ]

./mtc build "$repo/examples/ex1.c" -o "$tmp/hello"
[ "$("$tmp/hello")" = "Hello World" ]

./mtc lint "$repo/examples/ex1.c"
if ./mtc lint -Dtest_invalid_1 "$repo/tests/tests2/60_errors_and_warnings.c" 2>/dev/null; then
    echo "mtc lint accepted invalid C" >&2
    exit 1
fi

./mtc tcc -v >/dev/null
test -f "$MTC_CACHE_DIR/include/stddef.h"
test -f "$MTC_CACHE_DIR/libtcc1.a"
