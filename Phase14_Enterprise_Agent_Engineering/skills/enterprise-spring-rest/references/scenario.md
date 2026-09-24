# Scenario A — Add a paginated REST operation

Input: an approved fictional GET /items contract, the existing service, and authenticated identity mapping. If the contract is not settled, identify the unresolved choice before changing consumers.

Implement bounded pagination (example limit 1..100), DTO validation, and tenant-aware reads. Exercise empty results, invalid bounds, another tenant's resource, and ordinary success. Never accept an authoritative tenant from a prompt/body just to simplify the example.

Output: code diff, contract change, curl example with expected status/body, and actual test results. Explain any remaining assumptions about consumer compatibility.

In Phase 14, RunController, RunService, SecurityConfig, and static/openapi.json illustrate these boundaries. The lab has no inventory backend; do not describe its synthetic health data as a real API call.

Engineering practices: harness, context, tools, guardrails, evals, observability.
