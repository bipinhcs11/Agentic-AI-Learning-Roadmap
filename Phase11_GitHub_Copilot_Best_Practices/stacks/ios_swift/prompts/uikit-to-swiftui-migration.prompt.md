---
mode: agent
description: "Migrate ONE UIKit screen to SwiftUI — behavior pinned, navigation preserved"
---

# /uikit-to-swiftui-migration

**Role**: You migrate UIKit screens the way the ObjC prompt migrates classes: one
surface at a time, behavior pinned first, and the app never notices the seam.

**Context**: `ios-swift.instructions.md` applies. Screen to migrate:
${input:target:ONE view controller, e.g. "CardControlsViewController (UIKit, 600 lines, in Legacy/)"}
If this input names a flow of multiple screens or "the settings module", refuse and
ask for a single screen.

**Task**:
1. **Read the original**: lifecycle side effects (`viewDidLoad`/`viewWillAppear`
   work), delegate wiring, notification observers, timers, keyboard handling,
   trait-collection behavior. List what the screen *actually* does — surprises go
   to me before any SwiftUI.
2. **Pin behavior**: snapshot tests (if the repo has a snapshot harness) or UI/unit
   characterization tests against the UIKit screen, including rotation and Dynamic
   Type variants the original supported.
3. **Build the SwiftUI replacement** per the repo's architecture — state into a
   `@MainActor` view model, lifecycle work into `.task {}`/`onAppear` equivalents,
   delegate callbacks into async sequences or closures at the boundary.
4. **Host, don't rewire**: the new view ships inside `UIHostingController` behind
   the same navigation entry point — callers, storyboards/segues, and deep links
   compile and run untouched.
5. **Verify**: characterization/snapshot suite green against the SwiftUI version;
   list intentional visual diffs (none unless I approved them).

**Constraints**:
- Zero behavior change — quirks migrate too; UIKit bugs are reported, not silently
  fixed in the rewrite.
- No side-quest migrations: shared UIKit helpers the screen uses stay UIKit unless
  they are used by this screen alone.
- Accessibility parity is part of behavior: labels, identifiers, VoiceOver order,
  and Dynamic Type at least match the original — improvements listed separately.
- Navigation pattern comes from the repo's existing SwiftUI screens, not invented.

**Output**: The behavior inventory, pinned tests + first green run, the SwiftUI
view + view model + hosting shim, second green run, and the follow-up list
(UIKit files now orphaned, deletion criteria, reported quirks).

**Reference**: The repo's most recently migrated screen, or
${input:reference:e.g. kudoleh/iOS-Clean-Architecture-MVVM for the UIKit/SwiftUI seam}
