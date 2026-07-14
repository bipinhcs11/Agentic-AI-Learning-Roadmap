# AGENTS.md — agent contract for this repository

<!-- Read by GitHub Copilot (agent mode / coding agent) and other AI coding agents.
     Keep in sync with .github/copilot-instructions.md — this file is the
     tool-agnostic summary; that file is the Copilot-specific detail. -->

## Project

TODO: One paragraph — what this system is and who depends on it.

## Commands

- Build: `TODO`
- Test: `TODO`
- Lint: `TODO`
- Run locally: `TODO`

Work is complete only when build + test + lint pass.

## Boundaries for agents

- Small, verifiable changes; propose a plan before touching more than ~5 files.
- Follow existing repo patterns; name the pattern you followed in your summary.
- Reuse-first ladder before any new code: needed at all → exists in this codebase →
  in the stdlib/framework → in an installed dependency → only then write the minimum.
  State the rung you stopped at. The ladder never prunes safety content (validation,
  error handling, authorization, audit, tests, accessibility).
- No new dependencies without an explicit callout (see the dependency-audit skill).
- No secrets, tokens, or internal hostnames in code, tests, or config.
- Never weaken or delete tests to make a change pass.
- Security rules in `.github/instructions/security.instructions.md` are non-negotiable.
