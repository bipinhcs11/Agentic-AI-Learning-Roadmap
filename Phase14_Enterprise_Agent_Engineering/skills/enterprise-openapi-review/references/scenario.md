# Scenario B — A required response field disappears

Compare fictional inventory-v1.json and inventory-v2.json. In Phase 14 these live in src/main/resources/fixtures. The second version replaces required name with label.

Expected finding: removing the promised name field can break consumers; adding label does not preserve that guarantee. Suggest an additive/deprecation migration if requirements permit. Report the operation and response schema pointer.

The bundled ContractReview checks only required inline response fields/types for GET /items. Its output is evidence for those rules, not a full compatibility certificate. A complete assessment also needs reference resolution, request changes, auth/status rules, and consumer tests.

Output: compatibility report plus, if requested, a curated tool definition. A completed review may still conclude that release should be blocked.

Engineering practices: context, tool design, guardrails, evals.
