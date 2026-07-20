# justfile

default:
    just --list

build:
    python3 scripts/dev.py build

test-legacy:
    python3 scripts/dev.py test legacy

test-toolchain:
    python3 scripts/dev.py test toolchain

test:
    python3 scripts/dev.py test all

package:
    python3 scripts/dev.py package

ci:
    python3 scripts/dev.py ci

clean:
    rm -rf build dist

fmt:
    zig fmt mtcc.zig

lint file:
    ./build/mtcc lint {{file}}
