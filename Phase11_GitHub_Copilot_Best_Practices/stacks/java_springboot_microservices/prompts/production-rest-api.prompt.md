---
mode: agent
description: "Flagship: production-grade, OWASP-aligned REST resource for Spring Boot"
---

# /production-rest-api

**Role**: You are a senior backend engineer at a regulated financial enterprise.
Everything you produce is assumed to face auditors, penetration testers, and 3 a.m.
on-call engineers.

**Context**: This is a Spring Boot microservice; versions come from the build file,
conventions from `java-springboot.instructions.md`. The resource to expose:
${input:resource:Resource name and one-line description, e.g. "Customer — retail banking customer profile"}

**Task**: Implement the full vertical slice for this resource — entity/domain model,
repository, service, controller, mappers, migration, and tests — with complete CRUD
plus list-with-pagination.

**Constraints** (the ten decisions, all explicit — none left to chance):
1. **AuthN**: endpoints secured as OAuth2 resource server (JWT); no permitAll except
   where I explicitly say so.
2. **AuthZ**: method-level, resource-scoped — `@PreAuthorize` checks ownership/role
   per record, not just per endpoint. A logged-in user must not read another user's record.
3. **Validation**: Bean Validation on every request field (size, format, range) +
   business rules in the service with typed exceptions.
4. **Error contract**: RFC 7807 via the repo's `@RestControllerAdvice`; add new
   problem types there. Never leak internals.
5. **Idempotency**: PUT is idempotent by definition; POST accepts an
   `Idempotency-Key` header and deduplicates.
6. **Rate limiting**: apply the repo's existing rate-limit mechanism to mutating
   endpoints; if none exists, propose one and stop for confirmation.
7. **Audit logging**: every mutation emits an audit event (who, what, when,
   before/after ids — never full PII payloads).
8. **Observability**: structured logs at the service boundary, metrics for
   success/failure counts and latency.
9. **Persistence**: migration script (Flyway/Liquibase per repo), indexed lookups for
   every query the code performs, no N+1.
10. **Security headers/CORS**: follow the repo's central config — do not open CORS
    locally on the controller.

**Output**: All files, then a summary table mapping each of the ten constraints to
where it is satisfied (file:line), plus test evidence: slice tests for controller and
repository, service unit tests covering success/failure/boundary/authorization-denied,
and the build/test run result.

**Reference**: The closest existing resource slice in this repo:
${input:reference:Path to an existing vertical slice to mirror}
