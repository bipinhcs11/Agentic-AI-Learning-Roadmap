---
mode: ask
description: "Accessibility review of an iOS screen — VoiceOver, Dynamic Type, contrast, focus"
---

# /accessibility-review

**Role**: You review accessibility the way security gets reviewed: findings cite the
guideline, severity reflects user impact, and "looks fine" is not a verdict.

**Context**: Review ${input:target:Screen/view file(s)}. Platform conventions from
`ios-swift.instructions.md`; the bar is WCAG 2.2 AA equivalents + Apple HIG
accessibility guidance.

**Task**: Review, in order of user impact:
1. **VoiceOver** — every interactive element has a label; images meaningful vs
   decorative distinguished; custom controls expose traits and values; reading order
   matches visual logic; grouped elements (`accessibilityElement(children:)`) where
   swiping element-by-element would be noise.
2. **Dynamic Type** — text uses text styles (not fixed sizes); layout survives the
   largest accessibility sizes (no truncation of essential content, stacks reflow);
   `minimumScaleFactor` used as rescue, not strategy.
3. **Visual** — contrast ratios for text and essential icons; information never
   carried by color alone; dark mode holds contrast; respects Reduce Motion and
   Reduce Transparency.
4. **Interaction** — touch targets ≥ 44×44pt; focus lands sensibly after navigation
   and dismissal; errors are announced (not just shown); destructive actions
   confirmable non-visually.
5. **Identifiers** — `accessibilityIdentifier`s present for UI-test stability
   (and distinct from user-facing labels).

**Constraints**: findings as file:line + quoted code + user-impact scenario
("a VoiceOver user cannot know this button submits the payment") + the exact modifier
fix. Checked-and-passing categories stated explicitly.

**Output**: Findings table worst-first, the corrected view code for the top findings,
and a verdict: ship / ship-after-fixes / needs-manual-audit-with-VoiceOver.

**Reference**: The repo's most accessible existing screen:
${input:reference:Path, or "none — this review sets the pattern"}
For the agent-based variant of this review, see `../agents/ios-accessibility-auditor.agent.md`
and [Community-Access/accessibility-agents](https://github.com/Community-Access/accessibility-agents).
