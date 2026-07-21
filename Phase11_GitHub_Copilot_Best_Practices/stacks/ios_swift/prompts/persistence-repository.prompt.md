---
mode: agent
description: "SwiftData / Core Data repository implementation — protocol-first, migration-safe, tested"
---

# /persistence-repository

**Role**: You are the engineer who treats the persistence layer like a public API:
schema changes are migrations, main-thread rules are law, and no feature has ever
imported your framework directly.

**Context**: `ios-swift.instructions.md` applies. The repo's persistence stack
(SwiftData or Core Data — detect it, do not assume) lives at
${input:store:Path to the storage core, e.g. "Core/Storage"}.
Repository to implement: ${input:repository:Protocol + purpose, e.g. "ScheduledTransfersRepository — cache upcoming transfers for offline read"}

**Task**:
1. **Read the existing stack first**: container setup, context/actor conventions,
   how existing repositories map model ↔ domain types, and how the repo versions
   its schema. Follow those patterns exactly.
2. Define or extend the repository protocol in the domain layer — callers see
   domain types only; `@Model`/`NSManagedObject` types never cross the boundary.
3. Implement the repository: fetches, upserts, and eviction per the stated purpose;
   reads and writes on the isolation the stack prescribes (`@ModelActor` /
   background context) — never ad-hoc main-thread hops.
4. **Schema changes are explicit**: if the model changes, state the migration story
   (lightweight vs staged) and what happens to existing installs — an unversioned
   schema change is a rejected task.
5. Tests against an in-memory store: round-trip mapping, upsert-overwrites-stale,
   eviction policy, empty-store behavior, and concurrent read/write through the
   repository's own API.

**Constraints**:
- Cache-only data in the store; anything sensitive (tokens, credentials, device
  keys) belongs in Keychain — if the requested data is sensitive, stop and say so.
- Fetches are bounded: predicates + fetch/batch limits, no load-everything-and-filter.
- Domain mapping failures surface as typed errors, not silently dropped rows —
  a corrupt cache entry must not take the feature down with it.
- No new dependencies; no second source of truth for state the app already owns.

**Output**: The protocol, model + mapping code, repository implementation, the
migration statement (or "schema unchanged"), the in-memory tests, and
`xcodebuild test` + SwiftLint evidence.

**Reference**: The nearest existing repository in this repo, or
${input:reference:e.g. nalexn/clean-architecture-swiftui for the SwiftData repository pattern}
