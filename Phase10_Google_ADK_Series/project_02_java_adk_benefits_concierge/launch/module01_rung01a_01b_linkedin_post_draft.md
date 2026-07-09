# Social-Safe Draft - Module 01 Rungs 01A and 01B

Status: compliance-safe technical draft. Avoids sensitive product terms, vendor
names, and advice language.

I finished the first milestone in my Phase 10 Google ADK series:

a Java ADK concierge that can answer fictional workplace-policy questions, call
deterministic tools, and return a trusted A2UI-shaped payload.

This is not a chatbot wrapper.
And it is not "let the model generate some JSON."

The learning goal was more specific:

How do you build an agent whose skills, tools, safety boundaries, and UI output
are explicit enough to trust?

Rung 01A: Java ADK skill loop

The text answer is the visible part, but the real lesson is the execution path
behind it:

- Java ADK `LlmAgent` as the orchestrator
- deterministic Java tools for demo calculations
- local fictional knowledge for grounded explanations
- guardrails for real data, real transactions, and advice requests
- offline tests before adding a frontend

Example prompt:

"For this fictional plan, explain how the demo contribution estimate is
calculated."

The agent path is:

1. retrieve the fictional rule
2. calculate with Java `BigDecimal`, not LLM math
3. explain the result clearly
4. state that the answer is educational and fictional

Rung 01B: trusted A2UI payload

This is where the agent starts returning a UI-shaped answer.

But the model does not get to invent the frontend.

The Java side defines a trusted catalog:

- `Card`
- `Table`
- `Text`

The agent can return a projection card, but the payload is validated before any
renderer touches it.

Risky props such as `onClick`, `href`, `html`, and `script` are blocked.

The result is wrapped as:

`metadata.mimeType = application/json+a2ui`

So the browser is not receiving random JSON. It is receiving a constrained
agent-to-UI contract.

My takeaway:

A useful agent UI starts before the UI.

First make the agent's skill loop reliable.
Then make the UI output constrained and validated.
Only then render it.

Next: Rung 01C, React renders the trusted A2UI payload.

#GoogleADK #Java #AgenticAI #A2UI #AIEngineering
