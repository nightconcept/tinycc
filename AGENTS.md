# ⚠ This file is hard-limited to ≤100 lines. Update spokes, not the hub.

# TinyCC Agent Guide

## Intent

Maintain TinyCC and its thin ZTCC frontend with small, reviewable changes that
remain easy to rebase onto upstream TinyCC.

## Stack

- C90-oriented TinyCC compiler and GNU Make build
- Zig frontend (`ztcc.zig`)
- TinyCC compiler sources (`src/`)
- Single-purpose scripts in `scripts/` (build, test, package, ci), driven via
  `just` (tools pinned in `mise.toml`)

## Essential Commands

- **Tools**: `mise install` (zig, python, just, lefthook), then `just hooks-install`
- **Gate**: `just gate-fast` (fmt + zig unit tests, runs pre-commit) or
  `just gate` (adds build + legacy + toolchain tests, runs pre-push)
- **Build**: `just build` — out-of-tree configure+build into `build/` (objects,
  libs, `tcc`, `ztcc`); repo root and `src/` stay clean
- **Test legacy (vendored upstream TinyCC suite)**: `just test-legacy`
- **Test toolchain (ztcc CLI, not compilation)**: `just test-toolchain`
- **Test both, legacy first**: `just test`
- **Package**: `just package` — copies `build/ztcc` into `dist/`
- **Format Zig**: `zig fmt ztcc.zig`

## Engineering Standards

- Match surrounding code and avoid unrelated formatting changes.
- Keep TCC changes small enough to rebase `dev` onto `upstream/mob`.
- Use [Conventional Commits](https://www.conventionalcommits.org/) for commits,
  such as `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, and `chore:`.
- Run the smallest relevant test before committing; use `just test-legacy` for C
  changes and `just test-toolchain` for ZTCC changes. Legacy tests always gate
  before toolchain tests — `just test` enforces that order.

## Spoke Index

- [README](README) — project overview, installation, and usage
- [Coding style](src/CodingStyle) — C conventions and deeper testing guidance
