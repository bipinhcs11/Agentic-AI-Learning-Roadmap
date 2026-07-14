---
description: "Java Spring Boot microservice conventions"
applyTo: "**/*.java"
---

# Java / Spring Boot instructions

## Toolchain

- Target the Java LTS and Spring Boot version pinned in this repo's build file —
  read them from there; do not assume newer.
- Use the repo's build tool wrapper (`./gradlew` or `./mvnw`), never a global install.

## Architecture & layering

- Strict layering: `controller → service → repository`. Controllers hold zero business
  logic; repositories hold zero business logic; domain logic lives in services or the
  domain model.
- Constructor injection only — no field `@Autowired`. Dependencies are `final`.
- DTOs at the edges (records preferred); JPA entities never cross the controller
  boundary in either direction. Map explicitly (MapStruct or hand-written mappers,
  whichever this repo already uses).
- One `@Transactional` boundary at the service layer; never on controllers, never on
  repositories, and state readOnly where true.

## API contract

- Validation via Jakarta Bean Validation on request DTOs (`@Valid` at the controller);
  business-rule validation in the service with typed exceptions.
- Errors follow RFC 7807 (`ProblemDetail`) via a single `@RestControllerAdvice` —
  no per-controller try/catch, no stack traces in responses.
- Pagination on every collection endpoint (`Pageable`), explicit upper bound on page size.
- New/changed endpoints update the OpenAPI annotations in the same PR.

## Persistence

- Schema changes only through the migration tool this repo uses (Flyway/Liquibase) —
  never `ddl-auto` beyond `validate`.
- No N+1: collections are fetched deliberately (`@EntityGraph`, fetch joins, or
  projections). If unsure, say so and add the query test.

## Observability & resilience

- Logs via SLF4J, structured, parameterized (`log.info("order {} shipped", id)`) —
  no string concatenation, no `System.out`, no payload/PII logging.
- Every outbound HTTP call has a connect + read timeout and either a retry-with-backoff
  or an explicit decision not to retry (idempotency stated).
- Expose health via Actuator; new failure modes get a meaningful health indicator.

## Testing

- Slice tests where they fit (`@WebMvcTest`, `@DataJpaTest`); full `@SpringBootTest`
  only when the wiring itself is under test.
- Testcontainers for anything that talks to infrastructure; H2-pretending-to-be-Postgres
  is not a passing test.
- Follow the repo's universal testing instructions for the four-case coverage rule.
