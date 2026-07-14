# Repository instructions for GitHub Copilot

<!-- This file is injected into every Copilot chat/agent request in this repo.
     Keep it under ~60 lines. Every line here costs context on every request. -->

## What this project is

<!-- TODO: 3–5 lines. What the system does, who consumes it, what "done" means here. -->
TODO: One-paragraph description of this service/app and its consumers.

## Architecture in five lines

<!-- TODO: the load-bearing facts Copilot cannot infer from file names. Example:
     - Hexagonal architecture: domain/ has no framework imports.
     - All external calls go through adapters in infra/.
     - Events are the only cross-service communication. -->
TODO: List the architectural rules that survive code review.

## How to build, test, validate

<!-- Copilot agent mode runs these before declaring work complete. Be exact. -->

- Build: `TODO: e.g. ./gradlew build / npm run build / xcodebuild ...`
- Test: `TODO: e.g. ./gradlew test / npm test`
- Lint: `TODO: e.g. ./gradlew spotlessCheck / npm run lint`

A task is not complete until build, tests, and lint pass locally.

## Universal rules (apply to all generated code)

- Prefer small, verifiable changes. If a task needs to touch more than ~5 files,
  propose a plan first and wait for confirmation.
- Follow the existing patterns in this repo before inventing new ones. When in doubt,
  find the closest existing implementation and match it.
- **Before writing new code, walk this ladder and stop at the first rung that holds**:
  1. Does this need to exist at all? (If the requirement doesn't demand it, don't build it.)
  2. Does this codebase already do it? Reuse or extend that.
  3. Does the standard library or framework already do it? Use that.
  4. Does an already-installed dependency do it? Use that.
  5. Only then write new code — the minimum that satisfies the acceptance criteria.
  State which rung you stopped at when proposing non-trivial changes.
- The ladder never prunes safety: input validation, error handling, authorization,
  audit events, tests, and accessibility are requirements, not optional verbosity.
- Never hardcode secrets, tokens, connection strings, or internal hostnames.
  Configuration comes from the environment or the approved secret store.
- Every new public behavior needs a test: success, failure, and empty/edge case.
- Do not add new third-party dependencies without calling it out explicitly —
  dependencies go through the approved-library process.
- Do not delete or weaken existing tests to make a change pass.
- Generated code must compile against the versions pinned in this repo — do not
  assume newer language or framework features than the toolchain provides.

## What NOT to do

- Do not generate license headers, boilerplate comments, or restate what code does.
- Do not "improve" unrelated code in the same change (no drive-by refactors).
- Do not fabricate API endpoints, config keys, or library methods — if unsure,
  say so and point to where the answer would live.
