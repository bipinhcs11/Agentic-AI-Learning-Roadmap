---
description: "Objective-C estate rules — comprehension, containment, incremental migration"
applyTo: "**/*.{m,mm,h}"
---

# Objective-C instructions

This codebase's Objective-C is load-bearing legacy: assume every quirk may be
someone's contract. The goal is comprehension and containment — not rewriting.

## Working in the estate

- Match the file's existing style exactly — naming, bracket placement, `NS_ASSUME_NONNULL`
  usage. Consistency inside a legacy file beats modernity.
- When touching a header, add or correct nullability annotations
  (`nullable`/`nonnull`/`NS_ASSUME_NONNULL_BEGIN`) for the symbols you touch — this is
  the cheapest gift to Swift callers.
- Memory rules: name the retain-cycle risk whenever a block captures `self`
  (weak/strong dance where the block outlives the scope); flag any `assign` property
  that holds an object; respect non-ARC files if any exist — check before assuming ARC.
- Prefer fixing at the seam: if a method is unsafe, wrap it and deprecate
  (`API_DEPRECATED`) rather than editing twenty call sites in one change.

## Interop with Swift

- Public ObjC APIs intended for Swift get audited headers: nullability, generics on
  collections (`NSArray<NSString *>`), `NS_SWIFT_NAME` where the imported name is ugly.
- New async Swift wrappers around completion-handler ObjC APIs live in Swift extension
  files, not in the ObjC layer.
- Keep the bridging header minimal and sorted; never expose an ObjC type to Swift
  that has an un-annotated header.

## Migration discipline (non-negotiable)

- **One boundary per change**: one class, one feature, one seam — never "convert this
  module." A migration PR that touches more than one boundary gets split.
- Tests first: characterization tests (XCTest) pin the current ObjC behavior —
  including its quirks — before any Swift replaces it.
- The ObjC symbol keeps working during migration: Swift replacement lands behind the
  same interface, callers move incrementally, the ObjC original is deleted only when
  call-site count reaches zero (verify with search, state the count).
- Behavioral differences discovered during migration (bugs, undocumented behavior) are
  reported separately — never silently "fixed" inside the migration.
