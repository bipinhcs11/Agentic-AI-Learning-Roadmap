---
mode: agent
description: "Migrate ONE Objective-C boundary to Swift — tests pinned, interop preserved"
---

# /objc-to-swift-migration

**Role**: You are the engineer trusted with the legacy estate precisely because you
don't rewrite things — you migrate one boundary at a time and nothing breaks.

**Context**: `objective-c.instructions.md` and `ios-swift.instructions.md` apply.
Boundary to migrate: ${input:target:ONE class/seam, e.g. "PaymentFormatter (NSObject subclass, 400 lines)"}
If this input names more than one class or a whole module, refuse and ask for a
single boundary.

**Task**:
1. **Explain first**: what the ObjC code actually does — public contract, side
   effects, threading assumptions, quirks. Surprises go to me before any code.
2. **Pin behavior**: XCTest characterization tests against the existing ObjC
   implementation, including the quirks. Run them; show green.
3. **Audit the header**: nullability, collection generics, `NS_SWIFT_NAME` — so the
   Swift view of the contract is honest.
4. **Implement in Swift** behind the same interface: same class name via `@objc`
   bridging or a protocol both implementations satisfy — existing call sites compile
   untouched.
5. **Swap and verify**: characterization tests run green against the Swift
   implementation. Report call-site count for the ObjC original and where it can be
   deleted once callers move.

**Constraints**:
- Zero behavior change — quirks migrate too; suspected bugs are reported separately.
- Completion-handler APIs get async Swift wrappers only if the ObjC contract exposed
  them; do not redesign the API mid-migration.
- Memory semantics preserved and stated (what was `assign`/`weak`/`copy`, and what it
  became in Swift).

**Output**: The explanation, characterization tests + first green run, audited header
diff, Swift implementation, second green run, and the follow-up list (remaining
callers, deletion criteria, reported quirks).

**Reference**: The repo's most recently completed migration of this kind:
${input:reference:Path, or "none — this is the first"}
