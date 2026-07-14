---
mode: agent
description: "Functional HTTP interceptor (HttpInterceptorFn) with tests"
---

# /functional-interceptor

**Role**: You are an Angular engineer building the HTTP edge of an enterprise app —
the code every single request flows through, so boring and correct beats clever.

**Context**: `angular.instructions.md` applies. Interceptor to build:
${input:interceptor:Responsibility, e.g. "attach bearer token + correlation id; normalize 4xx/5xx into the app's ApiError; never touch asset requests"}

**Task**: Implement it as an `HttpInterceptorFn` registered via
`provideHttpClient(withInterceptors([...]))`, with unit tests.

**Constraints**:
- Functional style with `inject()` inside the fn — no class interceptors, no
  `HTTP_INTERCEPTORS` multi-provider.
- Scope guard first: define (and test) exactly which requests it applies to; skip
  assets/third-party origins explicitly.
- Immutable request handling — `req.clone()`, never mutation.
- Error mapping: typed error object, no swallowing; retries only for idempotent
  methods and only if the repo has a retry policy — otherwise don't invent one.
- Never log tokens or request bodies. Correlation id generation matches the repo's
  existing scheme if present.
- Order matters: state where this interceptor sits relative to existing ones and why.

**Output**: The interceptor, its registration diff, tests using HttpTestingController
(applies/skips scope, happy path, each mapped error class, no-token behavior), and
test-run evidence.

**Reference**: Existing interceptors in this repo, or the auth service that owns tokens:
${input:reference:Path}
