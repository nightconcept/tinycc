# ⚠ This file is hard-limited to ≤100 lines. Update spokes, not the hub.

# TinyCC Agent Guide

## Intent

Maintain TinyCC and its thin MTCC frontend with small, reviewable changes that
remain easy to rebase onto upstream TinyCC.

## Stack

- C90-oriented TinyCC compiler and GNU Make build
- Zig frontend (`mtcc.zig`)
- TinyCC compiler sources (`src/`)
- Shell-based smoke and release scripts

## Essential Commands

- **Configure**: `./src/configure`
- **Build**: `make` or `make mtcc`
- **Test**: `make test` or `make test-mtcc`
- **Format Zig**: `zig fmt mtcc.zig`
- **Lint C**: `./mtcc lint <file.c>` after building `mtcc`

## Engineering Standards

- Match surrounding code and avoid unrelated formatting changes.
- Keep TCC changes small enough to rebase `dev` onto `upstream/mob`.
- Use [Conventional Commits](https://www.conventionalcommits.org/) for commits,
  such as `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, and `chore:`.
- Run the smallest relevant test before committing; use `make test` for C changes
  and `make test-mtcc` for MTCC changes.

## Spoke Index

- [README](README) — project overview, installation, and usage
- [MTCC plan](PLAN.md) — frontend scope, packaging, branches, and remotes
- [Coding style](src/CodingStyle) — C conventions and deeper testing guidance
