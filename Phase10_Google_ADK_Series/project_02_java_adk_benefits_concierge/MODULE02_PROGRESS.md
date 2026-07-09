# Module 02 — UCP Benefits Transactions

Status: implemented (deterministic core + tests + demo). Built on Rung 01A and
reviewed for social-safe launch copy.

Module 02 is the transaction lane from the merged plan: the concierge moves from
advice to action. A fictional new hire enrolls in the Acme primary contribution and savings account, and
the plan they are eligible for depends on their employee category.

## The dynamic workflow

A UCP-shaped state machine (`UcpBenefitsTransactionService`):

```
PROPOSED ─▶ PENDING_APPROVAL ─▶ APPROVED ─▶ ENROLLED
                     │                 │
                     └────────── BLOCKED ◀── (no human confirmation)
```

- **propose** — look up the category's plan (UCP catalog), draft the election
  (cart), project the fixture amounts, and stage a mock pay-statement preview.
- **approve** — the human-approval gate. No confirmation ⇒ terminal `BLOCKED`;
  nothing is submitted.
- **checkout** — requires `APPROVED`; produces the order/receipt.
- Every transition appends to an audit trail, so the whole history is observable.

## UCP capability mapping

| UCP capability | Module 02 meaning |
|---|---|
| `catalog` | `BenefitsPlanCatalog.lookup(category)` → match tiers + savings account employer seed |
| `cart` | `ProposedElection` (primary contribution %, savings account amount, coverage) |
| `checkout` | `checkout(...)` — enforces 2026 fixture caps, requires approval |
| `order` | `EnrollmentReceipt` — confirmation id + the mock pay statement |

## Employee-category-driven match (same 6% deferral on $90k)

| Category | Employer match | savings account employer seed (family) |
|---|---|---|
| STANDARD | $4,050.00 | $1,000.00 |
| EXECUTIVE | $5,400.00 | $2,000.00 |
| PART_TIME | $1,350.00 | $0.00 |

## The payslip as A2UI

Note on A2UI + Java: Java ADK has **no** A2UI SDK — that is Python ADK 2.0 only
(`a2ui-agent-sdk`). A2UI itself is a language-agnostic JSON protocol, so Module
02 emits **A2UI-shaped JSON as a protocol contract** (hand-built component model
+ server-side validator), which is the documented Java path. Using the
first-class A2UI SDK "properly" is deferred to **Module 03 (Python ADK 2.0)**.

`UcpReceiptA2uiService` renders the receipt as a mock pay statement using
only the trusted catalog (`Card` / `Table` / `Text`), validated server-side.
Structure is kept compatible with the React renderer's stricter prop allowlist
(section titles are `Text`; tables carry only `columns` + `rows`).

Fixture: `docs/module02/a2ui-payslip-fixture.json` (schema
`a2ui.phase10.module02.v1`).

React integration note for Rung 01C: `react-a2ui-renderer/src/a2uiCatalog.js`
accepts both `a2ui.phase10.rung01b.v1` and `a2ui.phase10.module02.v1`, so this
fixture conforms to the renderer's component/prop rules.

## Files (all new, package `com.benefits.adk.ucp`)

- Domain: `EmployeeCategory`, `EmployeeProfile`, `BenefitsPlanOption`, `BenefitsPlanCatalog`, `ProposedElection`, `Payslip`, `EnrollmentReceipt`, `TransactionStatus`, `BenefitsTransactionState`
- Services: `PayslipService`, `UcpBenefitsTransactionService`, `UcpReceiptA2uiService`
- ADK-facing: `UcpBenefitsTransactionTools`, `BenefitsTransactionAgent`
- Runners: `UcpBenefitsTransactionDemoApp`, `ExportPayslipFixtureApp`
- Tests: `BenefitsPlanCatalogTest`, `UcpBenefitsTransactionServiceTest`, `PayslipServiceTest`, `UcpReceiptA2uiServiceTest`, `BenefitsTransactionAgentTest`

## How to run

```bash
# tests (16 Module 02 tests; 33 total incl. Rung 01A-01D)
mvn -o test -Dtest='BenefitsPlanCatalogTest,UcpBenefitsTransactionServiceTest,PayslipServiceTest,UcpReceiptA2uiServiceTest,BenefitsTransactionAgentTest'

# deterministic end-to-end demo (no Gemini needed)
mvn -q -o exec:java -Dexec.mainClass=com.benefits.adk.ucp.UcpBenefitsTransactionDemoApp

# regenerate the A2UI payslip fixture
mvn -q -o exec:java -Dexec.mainClass=com.benefits.adk.ucp.ExportPayslipFixtureApp
```

The `BenefitsTransactionAgent` (Gemini) wires the same tools for the live agent
path; the deterministic service/demo/tests need no cloud credentials.

## Guardrails

- Everything is fictional and educational; "ENROLLED" records nothing in a real
  system, account, or record system.
- No enrollment without an explicit human confirmation.
- 2026 fixture caps enforced in deterministic code (employee primary contribution $24,500;
  combined $72,000; savings account employee reduced so employee + employer seed ≤ coverage
  limit).
- Social drafts avoid named benefit products and vendor names; internal module
  docs/code keep the domain explicit because it is a fictional learning fixture.
- Taxes/true net pay omitted on purpose — not professional advice.

## Deliberately deferred

- Real AP2 payment authorization / real record system deduction (mock only).
- Persisted cross-call session state (tools are stateless; the service carries
  state within a call).
- First-class A2UI via the Python `a2ui-agent-sdk` — **Module 03 (Python ADK
  2.0)**, which will also cover A2A and render this payslip payload properly.
