# ⚠ This file is hard-limited to ≤100 lines. Update spokes, not the hub.

# TinyCC Agent Guide

## Intent

Maintain TinyCC and its thin MTC frontend with small, reviewable changes that
remain easy to rebase onto upstream TinyCC.

## Stack

- C90-oriented TinyCC compiler and GNU Make build
- Zig frontend (`mtc.zig`)
- Shell-based smoke and release scripts

## Essential Commands

- **Configure**: `./configure`
- **Build**: `make` or `make mtc`
- **Test**: `make test` or `make test-mtc`
- **Format Zig**: `zig fmt mtc.zig`
- **Lint C**: `./mtc lint <file.c>` after building `mtc`

## Engineering Standards

- Match surrounding code and avoid unrelated formatting changes.
- Keep TCC changes small enough to rebase `dev` onto `upstream/mob`.
- Use [Conventional Commits](https://www.conventionalcommits.org/) for commits,
  such as `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, and `chore:`.
- Run the smallest relevant test before committing; use `make test` for C changes
  and `make test-mtc` for MTC changes.

## Spoke Index

- [README](README) — project overview, installation, and usage
- [MTC plan](PLAN.md) — frontend scope, packaging, branches, and remotes
- [Coding style](CodingStyle) — C conventions and deeper testing guidance
