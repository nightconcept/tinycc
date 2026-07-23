# justfile

default:
    just --list

build:
    python3 scripts/build.py

test-legacy:
    python3 scripts/test_legacy.py

test-toolchain:
    python3 scripts/test_toolchain.py

test: test-legacy test-toolchain

package:
    python3 scripts/package.py

ci:
    python3 scripts/ci.py

clean:
    rm -rf build dist

fmt:
    zig fmt ztcc.zig

gate:
    python3 scripts/gate.py

gate-fast:
    python3 scripts/gate.py --fast

hooks-install:
    lefthook install
