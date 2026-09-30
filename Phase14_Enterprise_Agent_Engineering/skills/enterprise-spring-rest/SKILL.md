---
name: enterprise-spring-rest
description: Implement focused changes to existing Spring Boot REST endpoints with contract, tenant, and behavioral-test discipline.
---

# Spring REST change

Read [scenario instructions](references/scenario.md) for the concrete lab exercise and expected evidence.

Inspect the target build, endpoint contract, controller/service boundary, callers, and nearby tests before editing. Use the pinned framework generation and existing wrapper when present; use documented Maven otherwise. Preserve unrelated code and configuration.

Make the smallest vertical change across request validation, service rules, authorization, persistence, and response mapping. Derive tenant scope from trusted identity. Check resource ownership in the execution/data boundary; an ID in a URL is not authorization. Bound collection results and use the existing error-response convention.

Update the contract and usage instructions with changed behavior. Select tests for observable behavior and actual risks: invalid input, cross-tenant access, authorization, and the changed business outcome. Report commands and results, including tests not run. Do not introduce a new persistence framework, model provider, or deployment as an incidental cleanup.

Deliver a reviewable implementation, compatibility notes, and test evidence. Missing information that affects correctness deserves a focused question; routine choices can follow repository conventions.
