---
mode: agent
description: "Standalone Angular component with Signals state, typed IO, OnPush"
---

# /signals-component

**Role**: You are a senior Angular engineer on a design-system-driven enterprise app.

**Context**: Conventions in `angular.instructions.md` apply (standalone, Signals,
OnPush, new control flow). Component to build:
${input:component:Name + one-line responsibility, e.g. "TransactionList — paginated list of account transactions with status filter"}

**Task**: Implement the component pair — a container that owns data access and a
presentational component that renders it — plus tests.

**Constraints**:
- State via `signal`/`computed`; inputs with `input.required<T>()` where required;
  outputs with `output<T>()`. No `BehaviorSubject`-as-state, no `any`.
- Loading, empty, error, and populated states all rendered explicitly with `@if`/`@switch`;
  `@for` has `track`.
- Data access through an injected typed service; the presentational component performs
  zero HTTP.
- Accessibility: semantic elements, labels/aria where semantics fall short, visible
  focus, keyboard operability for anything clickable.
- Match this repo's design-system components — do not hand-roll a table/button/spinner
  if the library has one.

**Output**: Container + presentational component files, tests that drive them through
the DOM (states: loading, empty, error, populated, interaction event), and the test-run
evidence.

**Reference**: ${input:reference:Path to the closest existing component pair in this repo}
