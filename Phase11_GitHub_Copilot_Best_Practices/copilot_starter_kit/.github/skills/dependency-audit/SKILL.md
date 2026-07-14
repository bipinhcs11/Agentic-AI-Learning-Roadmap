---
name: dependency-audit
description: "Use when adding, upgrading, or reviewing a third-party dependency: checks license, maintenance health, supply-chain risk, and the enterprise approved-library process before any dependency change lands."
---

# Dependency Audit

When a task involves adding or upgrading a third-party dependency, run this checklist
BEFORE writing the dependency into any manifest (pom.xml, build.gradle, package.json,
Package.swift, requirements.txt).

## Checklist

1. **Need** — can the standard library or an already-approved dependency do this?
   A dependency that saves 30 lines is a liability, not a convenience.
2. **License** — permissive (MIT/Apache-2.0/BSD) is generally fine; copyleft
   (GPL/AGPL/SSPL) requires legal review in this enterprise. State the license found.
3. **Health** — last release date, open-issue trend, single-maintainer risk,
   known typosquat lookalikes of the name.
4. **Security** — check the advisory databases for the exact version being pinned;
   never float versions (`^`, `latest`, version ranges) in enterprise manifests.
5. **Blast radius** — transitive dependencies pulled in, size impact, native code.
6. **Process** — flag that this change needs the approved-library workflow entry;
   dependency changes never ride silently inside a feature PR.

## Output shape

A short verdict block in the PR description:

```
Dependency: <name>@<exact-version>
License: <spdx id> — <ok | needs legal review>
Health: <last release, maintainers, notable risks>
Advisories: <none found for this version | list>
Transitives: <count, notable ones>
Approved-library status: <already approved | request filed>
```

If any line cannot be verified with available tools, write "UNVERIFIED" — do not guess.
