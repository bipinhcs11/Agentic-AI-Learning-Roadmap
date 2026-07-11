---
mode: agent
description: "Strictly-typed Reactive Form with validation and accessible errors"
---

# /typed-reactive-form

**Role**: You are an Angular engineer who treats a form as a contract: every field
typed, every rule visible, every error reachable by screen reader.

**Context**: `angular.instructions.md` applies. Form to build:
${input:form:Fields + rules, e.g. "Beneficiary form — name (required), IBAN (format-validated), amount (positive, max 2dp), reference (optional, 140 chars)"}

**Task**: Implement the form component with full validation and submission wiring.

**Constraints**:
- `NonNullableFormBuilder`, explicit `FormGroup<...>` type — the model interface is
  written first and the form derives from it. No untyped `.value`.
- Validators: built-ins where they fit, custom validators as pure, separately-tested
  functions; cross-field rules at group level. Async validators debounce.
- Error UX: messages appear on touched-or-submitted (repo convention wins if it
  differs), each input `aria-describedby`s its error, first invalid control receives
  focus on failed submit.
- Submit: disabled only while in-flight (not while invalid — let users click and see
  errors), converts to the typed request model, handles server-side field errors by
  mapping them back onto controls.
- No `getRawValue()` sleight-of-hand around disabled-control semantics without a
  comment explaining the choice.

**Output**: Model interface, form component, custom-validator unit tests, DOM-level
component tests (valid path, each invalid rule, server-error mapping, a11y attributes),
test-run evidence.

**Reference**: ${input:reference:Path to the repo's best existing form}
