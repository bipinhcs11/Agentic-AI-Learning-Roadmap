# Stack Overlay — Java Spring Boot Microservices (Modules 1, 2, & 3 Blueprint)

Drop-on addition to the [generic starter kit](../../copilot_starter_kit/): copy the instructions, prompt files, custom agents, and skills into your repository's `.github/` folder.

This overlay incorporates **Claude Code-inspired agentic patterns** (Plan-Execute-Verify, subagent delegation, scoped context engineering, and test-driven self-correction) adapted specifically for **GitHub Copilot in VS Code**.

---

## Folder Structure

```
stacks/java_springboot_microservices/
├── java-springboot.instructions.md              # Universal Java 21 & Spring Boot 3.4+ rules
├── instructions/
│   ├── spring-boot-controller.instructions.md   # Path-scoped: **/controller/**/*.java
│   ├── spring-boot-service.instructions.md      # Path-scoped: **/service/**/*.java
│   └── spring-boot-repository.instructions.md   # Path-scoped: **/repository/**/*.java
├── prompts/
│   ├── production-rest-api.prompt.md            # Flagship OWASP REST API slice prompt
│   ├── spring-boot-resilience-circuitbreaker.prompt.md # Resilience4j & Micrometer metrics
│   ├── spring-boot-migration-upgrade.prompt.md  # Spring Boot 2.x to 3.4+ / Java 21 upgrade
│   └── spring-boot-security-owasp.prompt.md    # OWASP Top 10 security audit & fix prompt
├── agents/
│   ├── spring-architect.agent.md                # Subagent: DDD & Architecture Inspector
│   ├── spring-test-engineer.agent.md            # Subagent: Testcontainers & Quality Engineer
│   └── spring-security-auditor.agent.md          # Subagent: OWASP AppSec Auditor
└── skills/
    └── spring-boot-microservice-builder/
        └── SKILL.md                             # Executable Plan-Execute-Verify skill
```

---

## Contents & Capabilities

### Module 1: Instructions & Scoped Rules
- **`java-springboot.instructions.md`**: Pinned Java 21 LTS and Spring Boot 3.4+ standards (Virtual Threads, Records, MapStruct, RFC 7807 `ProblemDetail`, Resilience4j).
- **Path-Scoped Rules (`applyTo`)**: Focused instructions for `**/controller/**`, `**/service/**`, and `**/repository/**` to optimize token context.

### Module 2: Prompt Files (`.prompt.md`)
- **`/production-rest-api`**: Flagship 10-constraint prompt generating end-to-end production vertical slices.
- **`/spring-boot-resilience-circuitbreaker`**: Outbound HTTP resilience with Resilience4j `@CircuitBreaker`, `@Retry`, and Micrometer telemetry.
- **`/spring-boot-migration-upgrade`**: Upgrades legacy Spring Boot 2.x / Java 17 code to Spring Boot 3.4+ / Java 21 with Jakarta EE migration.
- **`/spring-boot-security-owasp`**: Performs comprehensive OWASP Top 10 Java audits and automated remediations.

### Module 3: Custom Agents, Skills & Presentation
- **Custom Agents**: `@spring-architect`, `@spring-test-engineer`, `@spring-security-auditor`.
- **Executable Skill**: `spring-boot-microservice-builder/SKILL.md` orchestrates end-to-end feature creation with test self-healing.
- **Presentation Deck Blueprint**: See [`docs/14_enterprise_presentation_deck_500_800_people.md`](../../docs/14_enterprise_presentation_deck_500_800_people.md) for the 500-800 audience presentation deck, live demo script, and Q&A handbook.

---

## Verification Commands

```bash
# Maven
./mvnw clean test

# Gradle
./gradlew clean test
```
