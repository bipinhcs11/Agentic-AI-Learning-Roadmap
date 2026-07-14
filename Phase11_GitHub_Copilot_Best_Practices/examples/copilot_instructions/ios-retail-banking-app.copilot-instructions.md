<!-- EXAMPLE: save as .github/copilot-instructions.md in an iOS banking app repo.
     Works in Copilot for Xcode too. Fictional app ("MobileBank-iOS") — rename, keep the shape. -->

# Repository instructions for GitHub Copilot

## What this project is

`MobileBank-iOS` is the retail banking app: accounts, transfers, check deposit,
card controls, secure messaging. Swift 6 / iOS 17+, SwiftUI for all new screens,
a legacy UIKit + Objective-C estate under `Legacy/` that still owns login and check
deposit. Release trains are biweekly through the bank's own signing pipeline —
a broken main branch blocks a train, so small verified changes only.

## Architecture in five lines

- Feature-based clean architecture: `Features/<Name>/{View,ViewModel,UseCase}`,
  data access behind protocols in `Core/Repositories`, DI via initializer injection
  composed in `AppComposition.swift` — no singletons, no service locators.
- ViewModels are `@MainActor @Observable`; each exposes ONE `state` value
  (enum: `.loading/.empty/.error(RetryableError)/.offline/.loaded(Content)`) —
  views switch over it exhaustively.
- Networking: `Core/Networking/APIClient` (async/await, certificate pinning,
  request signing) — no raw `URLSession` outside it, ever.
- Persistence: SwiftData for cache-only data via `Core/Storage`; anything sensitive
  (tokens, device binding keys) lives in Keychain via `SecureStore` — UserDefaults
  holds NOTHING customer-related.
- `Legacy/` (ObjC + UIKit): comprehension-and-containment rules apply — one-boundary
  migrations only, characterization tests first (see objective-c instructions file).

## How to build, test, validate

- Build + unit tests: `xcodebuild test -workspace MobileBank.xcworkspace -scheme MobileBank -destination 'platform=iOS Simulator,name=iPhone 16' -testPlan Unit`
- Lint: `swiftlint --strict` (config at `.swiftlint.yml` — strict means warnings fail)
- Snapshot tests: `-testPlan Snapshots` (run when touching any view; record mode is
  a deliberate, reviewed act — never commit re-recorded snapshots silently)
- A task is complete only when the Unit test plan and swiftlint pass locally.

## Banking-app rules (non-negotiable)

- **Concurrency**: structured only; UI state mutations `@MainActor`; every `Task`
  owned and cancelled (`.task {}` or stored + cancelled in `deinit`); no
  `Task.detached`, no `DispatchQueue` in async code, no `@unchecked Sendable`
  without a justifying comment.
- **Sensitive data**: no account numbers, balances, tokens, or customer names in
  logs, analytics events, or crash breadcrumbs — `Redactor.mask()` before any
  logging of model objects. Screens showing balances set
  `.privacySensitive()` (hidden in app switcher).
- **Session**: 5-minute idle lock via `SessionMonitor`; any new screen must be safe
  to disappear behind the lock at any moment (no unsaved-state loss, no completion
  handlers assuming foreground).
- **Money**: `Decimal` + `Core/Money` formatting (minor units from API) — never
  `Double`, never `NumberFormatter` inline.
- **Transfers & payees**: any mutation flow renders a signed confirmation summary
  from the SERVER response (never client-echoed input) and handles the
  step-up-authentication path (`AuthChallenge`) — omitting it fails review.
- **Accessibility**: Dynamic Type to accessibility sizes, VoiceOver labels on all
  controls, `accessibilityIdentifier` for UI tests; balance announcements use
  spelled-out currency (`AmountAccessibility.label(for:)`).
- **Offline**: read screens render cached data with a staleness banner; mutations
  queue nothing — they fail honestly with retry.

## What NOT to do

- No new third-party dependencies without the approved-library process — the app
  currently ships with four; keep it that way.
- No feature flags checked anywhere but `FeatureFlags` (server-driven) — no
  compile-time flag forests.
- No UIKit for new screens without an ADR — and no SwiftUI rewrites of `Legacy/`
  screens as a side effect of another task.
- Never weaken certificate pinning, jailbreak detection (`IntegrityCheck`), or
  the WebView allowlist "temporarily" — those diffs page the security team.
