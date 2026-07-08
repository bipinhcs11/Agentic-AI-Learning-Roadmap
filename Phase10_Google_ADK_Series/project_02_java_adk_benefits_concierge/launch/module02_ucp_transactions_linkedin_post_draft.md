# Social-Safe Draft - Module 02 UCP Transactions

Status: compliance-safe technical draft. Avoids sensitive product terms, vendor
names, and advice language.

Post idea:

The agent does not just answer. It can move through a bounded transaction lane.

Module 01 proved the Java ADK skill loop:

- deterministic tools
- trusted UI-shaped payloads
- server-side validation before browser rendering
- local-first tests

Module 02 adds the transaction boundary.

A fictional new hire starts from a proposed workplace election. The plan option
depends on an employee category, and the flow is intentionally narrow:

propose -> human approval -> checkout -> receipt

The important part is what the model does not control.

- It cannot skip the approval gate.
- It cannot submit anything without explicit confirmation.
- Demo limits are enforced in Java code, not left to model phrasing.
- The receipt is rendered from a trusted `Card` / `Table` / `Text` catalog.
- Declining approval ends in a `BLOCKED` state with nothing recorded.

That made UCP feel useful in exactly one place: the action lane.

The conversation can stay flexible.
The transaction path stays bounded.
The browser still renders only known components.

Stack:

- Java Google ADK
- deterministic UCP-shaped workflow
- audit trail for every state transition
- A2UI receipt from a trusted component catalog
- offline demo and JUnit coverage

Next: Module 03, where a second-agent boundary justifies A2A.

Fictional educational data only. Not professional advice.

#GoogleADK #Java #A2UI #UCP #AgenticAI #AIEngineering
