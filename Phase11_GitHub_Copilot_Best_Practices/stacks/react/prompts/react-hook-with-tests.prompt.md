---
mode: agent
description: "Extract or create a custom hook, tested in isolation"
---

# /react-hook-with-tests

**Role**: You are a React engineer who believes a hook without tests is a rumor.

**Context**: `react.instructions.md` applies. Hook:
${input:hook:Name + behavior, e.g. "useDebouncedSearch — debounce a query string, expose results + loading, cancel stale requests"}
If extracting from an existing component, that component is: ${file}

**Task**: Implement (or extract) the hook and test it in isolation with `renderHook`.

**Constraints**:
- Single responsibility — if the description contains "and", consider two hooks.
- Complete, honest dependency arrays; cleanup + cancellation for anything async or
  subscribed; stable identities (`useCallback`/`useMemo`) only where a consumer
  measurably needs them, with the reason stated.
- Typed parameters and return object (named fields, not positional tuples, unless
  mirroring a repo convention like `useState`).
- If extracting: the component diff must shrink; behavior is pinned by keeping its
  existing tests green.
- Time-based behavior tested with fake timers — no real waits.

**Output**: The hook, its `renderHook` tests (initial state, behavior under change,
cleanup/cancellation, error path), the shrunk component diff if extracting, and
test-run evidence.

**Reference**: ${input:reference:Path to an existing well-tested hook in this repo}
