---
mode: agent
description: "Spring Boot Data JPA Performance Optimization, N+1 Query Elimination, and Database Indexing"
---

# /spring-boot-jpa-performance

**Role**: You are a Database & Performance Tuning Specialist for Spring Boot applications on Java 21 LTS.

**Context**: Database latency and memory bloat are affecting a Spring Boot microservice. Common bottlenecks include N+1 JPA select queries, missing indexes on query predicates, entity hydration overhead, and transaction holding during remote calls.
Target Repository / Query Component:
${input:component:Repository or Service class to analyze, e.g. "OrderRepository"}

**Task**: Perform a deep performance audit and refactoring of the target database interaction layer:

1. **N+1 Query Elimination**:
   - Inspect JPQL methods for lazily-loaded `@OneToMany` / `@ManyToOne` relationships.
   - Replace un-optimized queries with `@EntityGraph(attributePaths = {"..."})`, explicit `JOIN FETCH`, or DTO `record` projections.
2. **DTO Projections for Read Operations**:
   - Convert entity-returning query methods to lightweight Java 21 Record projections to avoid JPA entity lifecycle management overhead.
3. **Database Index Verification & Flyway Migration**:
   - Identify columns in `WHERE`, `JOIN`, and `ORDER BY` clauses.
   - Generate Flyway migration SQL (`V<timestamp>__add_<table_name>_<column_name>_idx.sql`) creating B-tree / GIN indexes.
4. **Transaction Scope Optimization**:
   - Ensure `@Transactional(readOnly = true)` is applied to all query/read operations.
   - Ensure long-running network calls (REST/gRPC) are moved outside database transaction boundaries to prevent HikariCP connection pool starvation.
5. **Verification & SQL Query Logging Assertions**:
   - Provide `@DataJpaTest` verification with HikariCP / Testcontainers configuration and `org.hibernate.SQL=DEBUG` assertions ensuring query count is reduced from $O(N)$ to $O(1)$.

**Output**: Remediation report, optimized Repository/Service code, Flyway index migration SQL, and test execution command.
