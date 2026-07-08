# Social-Safe Draft - Module 01 Rungs 01C and 01D

Status: compliance-safe technical draft. Avoids sensitive product terms, vendor
names, and advice language.

I finished the browser side of my Phase 10 Google ADK Module 01 build.

The interesting part was not "make a React app."

The interesting part was this:

Can an agent produce a UI payload, stream it to the browser, and still keep the
frontend in control of what actually gets rendered?

That became two connected rungs:

- Rung 01C: React renders trusted A2UI-shaped JSON
- Rung 01D: AG-UI-style events stream that same payload live

Here is the flow:

1. Java ADK orchestrates the fictional concierge.
2. Deterministic Java tools calculate the demo projection.
3. The server creates an A2UI-shaped payload.
4. The payload is validated against a trusted catalog: `Card`, `Table`, `Text`.
5. React maps those known JSON types to known components.
6. A local Server-Sent Events stream sends live agent state to the browser.

The model does not get to invent arbitrary UI.
The agent does not send executable props.
The frontend does not mount unknown components.

That boundary matters.

A2UI gives the app a constrained UI payload.
AG-UI gives the app a live event flow.

Together, they let the agent drive a richer experience without giving up control
of the browser.

What this proved locally:

- Maven tests pass
- Vite build passes
- React renders the fictional projection rows
- the live stream reaches `finished`
- desktop and mobile browser checks pass
- no real account action is claimed or submitted

My takeaway:

Agent-driven UI should not mean model-controlled UI.

The agent can propose state.
The server can validate it.
The browser can render only trusted components.

Module 01 is now code/demo complete:

- 01A: Java ADK text agent
- 01B: trusted A2UI-shaped payload
- 01C: React renderer
- 01D: AG-UI-style streaming

Next: UCP transaction flow and A2A specialist agents.

Fictional educational data only. Not professional advice.

#GoogleADK #A2UI #AGUI #React #Java #AgenticAI
