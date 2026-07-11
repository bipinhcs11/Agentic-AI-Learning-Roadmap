---
description: "React conventions — typed function components, server-state discipline"
applyTo: "**/*.{tsx,jsx}"
---

# React instructions

## Components

- Function components + hooks only; TypeScript strict — no `any`, no `as` escapes
  without a comment justifying them.
- Props are explicit interfaces; no prop drilling past two levels — lift to context
  or composition instead.
- Business logic lives in hooks/services, not JSX. If a component is >150 lines,
  something wants extracting.
- Use the repo's design-system primitives — never hand-roll buttons, modals, tables
  the library already provides.
- Every async view renders all four states explicitly: loading, empty, error, populated.

## State

- **Server state belongs to the query library** this repo uses (TanStack Query/SWR/
  RTK Query) — never `useEffect` + `useState` fetching. Keys follow the repo's key
  factory convention; mutations invalidate what they change.
- Local UI state: `useState`/`useReducer`, kept as close to usage as possible.
- Global client state only for genuinely global things (session, theme, feature
  flags) using the store this repo already has — do not introduce a new one.
- Derive, don't duplicate: no copying props into state, no syncing two sources of
  truth with effects.

## Hooks & effects

- `useEffect` is for synchronizing with external systems — not for data fetching,
  not for computing derived values, not for reacting to state you also own.
  Most effects are a missing abstraction.
- Every effect: complete dependency array (no lint suppressions), cleanup function
  where anything is subscribed/scheduled, and cancellation for anything async.
- Reusable logic extracts to a custom hook with its own tests — components stay thin.

## Accessibility & quality

- Semantic HTML first; interactive elements are focusable, labeled, keyboard-operable.
- Forms use the repo's form library conventions; errors are announced
  (`aria-describedby`), not just colored red.
- Testing: React Testing Library idiom — assert what the user sees/does, not
  implementation internals. MSW (or repo equivalent) for network. Four-case coverage
  per the universal testing instructions.
