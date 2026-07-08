# Module 01 Social-Safe Launch Pack

Status: ready to post after normal human review. Drafts intentionally avoid
sensitive product terms, vendor names, and advice language.

Primary image:

```text
assets/module01_complete_google_style_architecture.png
```

Editable source:

```text
assets/module01_complete_google_style_architecture.svg
```

## Recommended Posting Order

1. `module01_rung01a_01b_linkedin_post_draft.md`
   - Image: `assets/architecture_diagram_benefits_concierge.png`
   - Angle: Java ADK skill loop plus trusted A2UI contract.
2. `module01_rung01c_01d_linkedin_post_draft.md`
   - Image: `assets/module01_complete_google_style_architecture.png`
   - Angle: React renders validated A2UI JSON, then AG-UI-style streaming updates the browser live.
3. Optional recap post below.

## Suggested Posting Window

For this technical architecture post, prefer one of these Central Time windows:

- Tuesday 10:00-11:30 AM CT
- Wednesday 10:00-11:30 AM CT
- Wednesday 3:00-4:00 PM CT

Avoid posting this one late on Thursday afternoon unless you are deliberately
testing that slot again. The post is dense and architecture-heavy, so it likely
needs a window where people have enough attention to read and inspect the image.

## Module 01 Recap Post

Module 01 of my Phase 10 Google ADK series is code/demo complete.

The project uses a fictional workplace-policy concierge. The point was not to
build a real employee system. The point was to learn how an ADK agent can move
from a plain text answer to a browser UI without letting the model own unsafe
parts of the system.

The rungs:

- 01A: Java ADK text agent
- 01B: trusted A2UI-shaped payload
- 01C: React renders the A2UI JSON
- 01D: AG-UI-style streaming updates browser state live

The architecture that emerged:

1. Java ADK handles orchestration.
2. Deterministic Java tools handle math and business rules.
3. Guardrails block real data, real transactions, and advice requests.
4. A trusted A2UI catalog limits what the agent can ask the UI to render.
5. React maps known JSON component types to known browser components.
6. AG-UI-style events stream progress and state to the browser.

The important distinction:

A2UI defines the safe UI payload.
AG-UI defines the live event flow.

Together, they let the agent drive a richer user experience while the app keeps
control of what is actually rendered or executed.

Verified locally:

- Maven tests pass
- Vite build passes
- React renders fictional projection rows
- live stream reaches `finished`
- desktop and mobile browser checks pass
- no real account action is claimed or submitted

Next, the roadmap splits:

- Module 02: UCP transaction lane with human approval boundaries
- Module 03: Python ADK 2.x A2A specialist agents

Fictional educational data only. Not professional advice.

#GoogleADK #AgenticAI #A2UI #AGUI #Java #React #AIEngineering
