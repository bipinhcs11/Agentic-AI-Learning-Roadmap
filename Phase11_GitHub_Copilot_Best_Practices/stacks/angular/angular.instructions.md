---
description: "Angular conventions — standalone, Signals-first, strictly typed"
applyTo: "**/*.ts"
---

# Angular instructions

## Baseline (do not generate legacy patterns)

- Standalone components only — no new NgModules.
- Signals are the default for component state: `signal`, `computed`, `input()`,
  `output()`, `model()`. Use RxJS where streams genuinely fit (events over time,
  cancellation, backpressure) — convert at the edge with `toSignal`/`toObservable`,
  and never mix both idioms for the same piece of state.
- `changeDetection: ChangeDetectionStrategy.OnPush` on every component.
- `inject()` over constructor injection in new code; match whichever the surrounding
  file already uses.
- New control flow (`@if`, `@for` with mandatory `track`, `@switch`) — not
  `*ngIf`/`*ngFor`.
- Lazy-load routes by default; `loadComponent`/`loadChildren` with route-level
  providers where scoping matters.

## Components

- Presentational vs container split: components that fetch don't render detail;
  components that render detail take `input()`s. No HTTP calls inside presentational
  components.
- Templates stay declarative — complex derivations move to `computed()`s, not template
  expressions or methods called from templates.
- Every interactive element is keyboard-reachable and labeled — ARIA attributes are
  part of the definition of done, not a follow-up.

## Data & forms

- HTTP through typed services returning typed models — no `any`, no raw `HttpClient`
  in components.
- Reactive Forms strictly typed (`FormGroup<{...}>`, `NonNullableFormBuilder`).
  Template-driven forms only for trivial single-field cases.
- Interceptors are functional (`HttpInterceptorFn`); auth tokens, correlation ids,
  and error normalization live there — never per-request in services.
- Loading/empty/error states are explicit in both state and template for every
  async view.

## Testing

- Component tests interact through the DOM (harnesses/testing-library idiom this repo
  uses) — not by poking component internals.
- HttpTestingController for HTTP; no real network. Follow the repo's universal
  testing instructions for four-case coverage.
