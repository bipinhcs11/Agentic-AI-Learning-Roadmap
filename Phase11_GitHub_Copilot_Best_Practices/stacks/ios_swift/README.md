# Stack Overlay — iOS (Swift, Objective-C, SwiftUI, UIKit)

Drop-on addition to the [generic starter kit](../../copilot_starter_kit/). Everything
universal — instructions, prompt files, agents, skills, hooks, MCP, model selection,
small verifiable tasks — applies to iOS unchanged. This overlay covers only what is
**genuinely different** about Apple development.

**Copilot surface**: [GitHub Copilot for Xcode](https://github.com/github/CopilotForXcode)
supports Swift and Objective-C with completions, chat, agent mode (including MCP
tools), code review, next-edit suggestions, Copilot Vision, BYOK — and, as of the
recent agentic releases, custom agents, subagents, and Plan Mode. Don't confuse
the official extension with
[intitni/CopilotForXcode](https://github.com/intitni/CopilotForXcode), the earlier
community project it grew out of — enterprise installs want the `github/` one.

### What actually works in Xcode (the part everyone gets wrong)

The general Copilot docs lag the extension. Per the extension's own
[Docs/CustomInstructions.md](https://github.com/github/CopilotForXcode/blob/main/Docs/CustomInstructions.md)
and [Docs/PromptFiles.md](https://github.com/github/CopilotForXcode/blob/main/Docs/PromptFiles.md):

| Surface | In Xcode? | Notes |
|---|---|---|
| `.github/copilot-instructions.md` | ✅ | auto-applies to all chat requests |
| `*.instructions.md` with `applyTo` | ✅ | path-scoped — this overlay's two files work as-is |
| `.github/prompts/*.prompt.md` | ✅ (experimental) | workspace prompt files — all 11 prompts here run in Xcode |
| Custom agents / subagents / Plan Mode | ✅ | recent agentic releases |
| MCP servers | ✅ | agent mode; see `mcp.json` below |
| Skills, hooks, `AGENTS.md` | not documented for Xcode | treat as VS Code / CLI surfaces for now |

So the committed-files blueprint works for iOS teams in full, and mixed teams
(VS Code for services, Xcode for the app) share one `.github/` setup — nothing in
this overlay is "VS Code-only".

One more reason this overlay exists: the community library
([github/awesome-copilot](https://github.com/github/awesome-copilot)) has, as of
2026-07, **no iOS app-engineering content at all** — its only Swift assets target
server-side MCP development. iOS teams start from zero; this folder is the zero.

## The core iOS principle

> Copilot does not know your iOS architecture merely because it can generate Swift.

Never prompt "build a production-grade iOS app using SwiftUI." Give it: minimum iOS
version, Xcode/Swift version, SwiftUI vs UIKit per surface, architecture and folder
structure, state-management approach, concurrency expectations, networking/persistence
choices, testing and accessibility requirements, and the exact build/validation
commands. That is precisely what `ios-swift.instructions.md` pins — once, in a file,
instead of per prompt.

## Contents

| File | What it does |
|---|---|
| `ios-swift.instructions.md` | Swift + SwiftUI guardrails: concurrency, MainActor, state ownership, view hygiene, testing, privacy |
| `objective-c.instructions.md` | Rules for the legacy estate: interop, nullability, memory, incremental migration only |
| `walkthrough.md` | **One feature end to end** — ticket → analysis → data → UI → tests → three reviews → PR, with the exact prompt at each step |
| `prompts/swiftui-feature.prompt.md` | Production-grade SwiftUI feature slice (View + ViewModel + tests, all view states) |
| `prompts/uikit-to-swiftui-migration.prompt.md` | Migrate ONE UIKit screen to SwiftUI — behavior pinned, hosting + navigation preserved |
| `prompts/objc-to-swift-migration.prompt.md` | Migrate ONE boundary from Objective-C to Swift, interop preserved, tests first |
| `prompts/networking-layer.prompt.md` | Add an endpoint behind the repo's protocols — error taxonomy, cancellation, tests |
| `prompts/persistence-repository.prompt.md` | SwiftData / Core Data repository — protocol-first, migration-safe, in-memory tested |
| `prompts/swift-concurrency-review.prompt.md` | Review for concurrency + memory: actor isolation, retain cycles, task lifecycle |
| `prompts/xctest-generation.prompt.md` | XCTest / Swift Testing generation with the four-case rule |
| `prompts/accessibility-review.prompt.md` | VoiceOver, Dynamic Type, contrast, focus — reviewed like security |
| `prompts/ios-performance-review.prompt.md` | App-startup + scrolling review — main-thread work, `body` cost, list hygiene, named Instruments experiments |
| `prompts/privacy-secure-storage-review.prompt.md` | Keychain discipline, logging redaction, privacy manifest, data-at-rest |
| `prompts/ios-pr-review.prompt.md` | Whole-diff PR review: scope, boundaries, edge states, tests — the last machine pass before a human |
| `agents/legacy-estate-analyst.agent.md` | Read-only ObjC-estate agent: header honesty, interop risk, migration-readiness scoring |
| `agents/ios-accessibility-auditor.agent.md` | Read-only accessibility audit agent — the security-reviewer pattern applied to VoiceOver/Dynamic Type |
| `mcp.json` | iOS MCP overlay: XcodeBuildMCP + simulator control, allowlist-scoped — lets agent mode actually build and test |
| `ci_ios.yml` | Actions workflow enforcing the instructions file's own commands (macOS runner, xcodebuild test, SwiftLint strict, xcresult artifact) |
| `skills/privacy-manifest-audit/` | Skill: audits `PrivacyInfo.xcprivacy` against actual required-reason API usage, collected data, SDK manifests |

That is the full set of iOS prompt categories worth standardizing — eleven files
covering twelve jobs (memory-leak / retain-cycle review lives inside
`/swift-concurrency-review`, where the evidence is). Every prompt keeps the same
6-part contract as the rest of the blueprint: Role → Context → Task → Constraints
→ Output → Reference.

## Reference repositories (use as *pattern attachments*, not templates to clone)

Point Copilot's **Reference** line at these when asking for a specific pattern —
"follow the layering in clean-architecture-swiftui" beats paragraphs of description.
All verified live and unarchived via the GitHub API; star counts as of 2026-07.

**Architecture references**

| Repo | Stars | Why |
|---|---|---|
| [nalexn/clean-architecture-swiftui](https://github.com/nalexn/clean-architecture-swiftui) | 6.6k | SwiftUI + clean architecture, async/await, DI, tests, SwiftData |
| [kudoleh/iOS-Clean-Architecture-MVVM](https://github.com/kudoleh/iOS-Clean-Architecture-MVVM) | 4.4k | MVVM with domain/data/presentation layers, DTOs, coordinators, UIKit & SwiftUI |
| [pointfreeco/swift-composable-architecture](https://github.com/pointfreeco/swift-composable-architecture) | 14.8k | State management, feature composition, testability |

**Engineering-quality references**

| Repo | Stars | Why |
|---|---|---|
| [realm/SwiftLint](https://github.com/realm/SwiftLint) | 19.7k | Enforce repo conventions deterministically — the linter, not instructions, owns style |
| [nicklockwood/SwiftFormat](https://github.com/nicklockwood/SwiftFormat) | 8.9k | Deterministic formatting — pair with SwiftLint so style never reaches review |
| [airbnb/swift](https://github.com/airbnb/swift) | 2.7k | A citable style guide — "follow airbnb/swift" is one Reference line, not forty rules |
| [krzysztofzablocki/Sourcery](https://github.com/krzysztofzablocki/Sourcery) | 8k | Codegen for mocks/boilerplate — pair with Copilot instead of hand-generating |
| [ochococo/Design-Patterns-In-Swift](https://github.com/ochococo/Design-Patterns-In-Swift) | 15.3k | Canonical Swift pattern implementations to cite by name |

**Testing references**

| Repo | Stars | Why |
|---|---|---|
| [Quick/Quick](https://github.com/Quick/Quick) | 9.8k | BDD tests for Swift & Objective-C |
| [pointfreeco/swift-snapshot-testing](https://github.com/pointfreeco/swift-snapshot-testing) | 4.3k | The snapshot harness the walkthrough's UIKit migration step leans on |
| [swiftlang/swift-testing](https://github.com/swiftlang/swift-testing) | 2.2k | The modern `@Test` framework `/xctest-generation` auto-detects |

**Toolchain & release references**

| Repo | Stars | Why |
|---|---|---|
| [fastlane/fastlane](https://github.com/fastlane/fastlane) | 41.8k | Release automation — the lanes are the "exact validation commands" your instructions should cite |
| [tuist/tuist](https://github.com/tuist/tuist) | 5.7k | Project generation at scale — one source of truth for targets Copilot can read |

**Framework implementation references**

| Repo | Stars | Why |
|---|---|---|
| [Alamofire/Alamofire](https://github.com/Alamofire/Alamofire) | 42.4k | Networking patterns, request handling, concurrency |
| [ReactiveX/RxSwift](https://github.com/ReactiveX/RxSwift) | 24.6k | Maintaining existing reactive codebases (legacy estates) |

**Agent tooling — MCP servers** (see `mcp.json`)

| Repo | Stars | Why |
|---|---|---|
| [getsentry/XcodeBuildMCP](https://github.com/getsentry/XcodeBuildMCP) | 6.1k | Build/run/test + simulator control for agent mode — the highest-leverage iOS MCP |
| [mobile-next/mobile-mcp](https://github.com/mobile-next/mobile-mcp) | 5.5k | Cross-platform device/simulator automation (iOS + Android) |
| [joshuayoes/ios-simulator-mcp](https://github.com/joshuayoes/ios-simulator-mcp) | 2.1k | Simulator inspection/interaction — pairs with the accessibility auditor |

## MCP: make the agent build and test, not describe building and testing

The generic kit's MCP governance (docs/06) applies unchanged: allowlisted servers,
platform-team ownership, no credentials in config. What's iOS-specific is the
payoff — with [XcodeBuildMCP](https://github.com/getsentry/XcodeBuildMCP) wired
in, "run `xcodebuild test` and show the evidence" stops being an instruction the
model narrates and becomes a tool call it executes: scheme discovery, builds,
test runs, and simulator control from agent mode, in Xcode or VS Code. `mcp.json`
in this folder holds the reviewed overlay entries (pin versions; start with
xcodebuild alone, add the simulator server when a workflow needs it).

## CI: where "done" is decided

`ci_ios.yml` is the enforcement half of the instructions file: the same
`xcodebuild test` + `swiftlint --strict` the agent must run locally, re-run on a
macOS runner with the `.xcresult` uploaded as the reviewable evidence. Lint is a
separate fast job; snapshot tests are a deliberate, visible step.

Two governance notes that are easy to get wrong:

- **The cloud coding agent cannot build your app.** GitHub's cloud Copilot
  coding agent executes on Linux — no `xcodebuild`, no simulators. Assign it
  SPM-package, lint, docs, and Linux-testable work; the app target's authority
  is this workflow on a macOS runner. Burning cloud-agent runs on Mac-only
  verification produces confident PRs with unverified builds.
- **The security-scan hook speaks iOS too.** The blueprint's
  [security-scan hook](../../examples/hooks/security-scan/) now carries iOS
  rules: ATS weakening (`NSAllowsArbitraryLoads`), debuggable entitlements
  (`get-task-allow`), and credential-shaped keys landing in plists or xcconfig
  instead of the Keychain — caught mechanically at edit time, before CI ever
  sees the diff.

## Objective-C deserves its own strategy

Enterprise iOS usually means a large, load-bearing Objective-C estate, not greenfield.
Copilot's highest-value ObjC work is **comprehension and containment**, not rewriting:
explaining legacy code, generating nullability annotations, wrapping
completion-handler APIs in async Swift, spotting retain-cycle risks, creating
Swift-compatible headers, and building XCTest cases around current behavior *before*
anything moves.

The one warning that saves quarters of pain:

> Do not ask Copilot to convert an entire Objective-C module to Swift in one request.
> Migrate one boundary, one class, one feature at a time — tests pinned, interop
> preserved. That is what `/objc-to-swift-migration` enforces.
