---
name: "spring-boot-microservice-builder"
description: "Executable Agentic Skill: End-to-End Enterprise Java 21 / Spring Boot 3.4+ Microservice Feature Builder following Plan-Execute-Verify"
---

# Enterprise Spring Boot Microservice Builder Skill

## Overview

This skill provides a structured, agentic workflow (inspired by Claude Code CLI patterns adapted for GitHub Copilot in VS Code) to design, build, refactor, test, and audit an enterprise-grade Java 21 / Spring Boot 3.4+ microservice feature.

---

## Workflow Steps

### Step 1: Context & Architecture Planning (Plan Phase)
1. Read project build descriptor (`pom.xml` or `build.gradle`) to determine pinned dependencies (Spring Boot, Java version, MapStruct, Resilience4j, Flyway).
2. Read `.github/instructions/java-springboot.instructions.md` and path-scoped instructions (`spring-boot-controller`, `spring-boot-service`, `spring-boot-repository`).
3. Formulate an explicit **Implementation Plan** listing all files to be created/modified across layers (`controller → service → repository → DTO → Flyway → Test`).

---

### Step 2: Persistence & Migration Layer Execution
1. Create Flyway SQL migration script under `src/main/resources/db/migration/V<timestamp>__create_<entity>_table.sql`.
2. Define indexed columns for all query parameters.
3. Create JPA Entity extending base audited entity fields (`@CreatedDate`, `@LastModifiedDate`).
4. Create Spring Data JPA Repository interface with explicit `@EntityGraph` or Record projections to prevent N+1 queries.

---

### Step 3: Domain & Service Layer Execution
1. Create immutable request and response DTOs using Java 21 `record` syntax. Add Jakarta Bean Validation annotations (`@NotNull`, `@Size`, `@Pattern`).
2. Create MapStruct mapper interface for DTO ↔ Entity translation.
3. Create Service implementation annotated with `@Transactional`.
4. Wrap outbound client calls with Resilience4j `@CircuitBreaker` and `@Retry`.
5. Implement idempotency key checking for mutating POST/PUT operations.

---

### Step 4: Controller Layer Execution
1. Create REST Controller annotated with `@RestController` and `@RequestMapping`.
2. Annotate methods with `@PreAuthorize` for method-level JWT scope verification.
3. Annotate request body parameters with `@Valid`.
4. Depend on global `@RestControllerAdvice` returning RFC 7807 `ProblemDetail` responses.

---

### Step 5: Test Execution & Self-Correction (Verify Phase)
1. Generate `@WebMvcTest` controller slice test verifying happy path (200/201), Bean validation failure (400), and access denied (403).
2. Generate Testcontainers integration test running against real PostgreSQLContainer.
3. Execute local build validation using `./mvnw test` or `./gradlew test`.
4. If tests fail, inspect exact failure logs, apply targeted fixes, and re-run tests until 100% green.

---

## Verification Commands

```bash
# Maven
./mvnw clean test

# Gradle
./gradlew clean test
```
