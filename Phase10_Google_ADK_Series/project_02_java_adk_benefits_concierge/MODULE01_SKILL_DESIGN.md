# Module 01 Skill Design - Rung 01A

Status: implemented for Rung 01A text agent.

This document is the lightweight Phase A sketch from
`PHASE10_PLAN_MERGED_for_review.md`. It keeps the first build focused on Java
ADK text orchestration and does not introduce React, AG-UI, UCP, or A2A yet.

## Skill Map

| Skill | Input | Output | Rung 01A behavior | Later UI state |
|---|---|---|---|---|
| Benefits education | Plain-language 401(k)/HSA question | Grounded explanation plus caveats | Uses local fictional KB through the retrieval tool | Education card |
| Retrieval + citation | Topic and user question | Relevant snippets and source ids | Local adapter stands in for managed Agent Search until cloud config exists | Citation list |
| Projection | Salary, 401(k) percent, HSA amount, coverage | Deterministic match/tax estimate | Java calculator tool, no LLM math | Projection table |
| A2UI projection card | Projection inputs | Trusted `Card` + `Table` + `Text` payload | Rung 01B validation scaffold only | ADK web UI verification payload |
| Election drafting | Requested contribution change | Non-executable draft summary | Produces a draft only; no commit path | Draft election panel |
| Approval gating | Draft action and user confirmation | Allowed/blocked decision | Blocks all commits in Rung 01A | Confirmation modal |
| Transaction execution | Confirmed transaction request | Receipt | Out of scope until Module 02 UCP | Receipt state |
| Optional specialist | Specialist task | Remote agent answer | Out of scope until Module 03 A2A | Specialist panel |

## Guardrail Boundaries

- The agent is educational and fictional; it must not claim to access real
  payroll, HRIS, provider, account, or customer data.
- It may calculate examples from user-provided numbers, but it must label them
  estimates.
- It must not provide legal, tax, investment, fiduciary, or individualized
  financial advice.
- It must not execute benefit elections, move money, open accounts, or update
  real records.
- Any election discussion must remain a draft until a future UCP confirmation
  lane exists.

## Rung 01A Success Criteria

- Java ADK root agent exists and exposes deterministic tools.
- Core benefits calculations are covered by offline JUnit tests.
- Retrieval returns fictional KB snippets with citation ids.
- Guardrail checks block real-data and transaction requests.
- Eval fixtures describe the expected judge criteria for the text agent.

## Rung 01B Verification Notes

- The Java code now has a trusted A2UI-shaped payload model and server-side
  validator for `Card`, `Table`, and `Text`.
- The exposed ADK tool wraps the validated payload with
  `metadata.mimeType = application/json+a2ui`.
- The validator rejects untrusted component types and executable props such as
  `onClick`, `href`, `html`, and `script`.
- Official Java A2UI Dev UI rendering still needs hands-on verification before
  this becomes the default response path.

## Deliberately Deferred

- A2UI payloads and server-side catalog validation move to Rung 01B.
- React rendering moves to Rung 01C.
- AG-UI streaming moves to Rung 01D.
- UCP transaction execution moves to Module 02.
- A2A specialists move to Module 03.
