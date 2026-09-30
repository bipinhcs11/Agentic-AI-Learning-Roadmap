---
name: "spring-boot-troubleshooter"
description: "Executable Agentic Skill: Production Incident Diagnostic & Automated Root Cause Analysis (RCA) for Spring Boot Microservices"
---

# Spring Boot Production Incident Troubleshooter Skill

## Overview

This skill provides a structured diagnostic workflow for troubleshooting runtime exceptions, transaction timeouts, database connection pool exhaustion, and memory leaks in Java 21 / Spring Boot 3.4+ microservices.

---

## Diagnostic Workflow

### Step 1: Exception Trace & Log Sanitization (Inspect Phase)
1. Read the provided stack trace, Actuator health output, or log excerpt.
2. Verify that no raw PII, account tokens, or secrets are present in the diagnostic log.
3. Identify the failing root cause component (`Controller`, `Service`, `Repository`, `Downstream RestClient`, `SecurityFilterChain`).

---

### Step 2: Diagnostic Categorization
- **Category A: Transaction / Locking Issue** -> `@Transactional` boundary missing, long-running HTTP call inside DB transaction, deadlocks.
- **Category B: Database / Connection Pool Exhaustion** -> HikariCP leak, unclosed connections, slow un-indexed queries.
- **Category C: Resilience / Timeout Failure** -> Downstream service timeout, missing Resilience4j CircuitBreaker fallback.
- **Category D: Security / Authorization Denial** -> Invalid JWT scope, `@PreAuthorize` evaluation failure, CORS misconfiguration.

---

### Step 3: Targeted Remediation & Code Diff
1. Generate the exact minimal code change to fix the underlying defect without introducing side effects.
2. Provide Flyway index migration SQL if slow query execution caused the timeout.
3. Add a regression test reproducing the exact failure scenario and verifying the fix.

---

### Step 4: Verification Command
```bash
./mvnw clean test -Dtest=*IntegrationTest
```
