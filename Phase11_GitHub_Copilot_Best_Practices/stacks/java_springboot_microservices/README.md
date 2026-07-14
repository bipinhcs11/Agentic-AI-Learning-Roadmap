# Stack Overlay — Java Spring Boot Microservices

Drop-on addition to the [generic starter kit](../../copilot_starter_kit/): copy
`java-springboot.instructions.md` into your repo's `.github/instructions/` and the
prompts into `.github/prompts/`. The generic kit stays unchanged underneath.

## Contents

| File | What it does |
|---|---|
| `java-springboot.instructions.md` | Path-scoped rules for all `**/*.java` — layering, DI, transactions, error contract, observability |
| `prompts/production-rest-api.prompt.md` | The series' flagship prompt: a production-grade, OWASP-aligned REST resource — auth, validation, RFC 7807 errors, rate limiting, audit logging, tests |
| `prompts/k8s-manifests.prompt.md` | Deployment/Service/HPA with enterprise defaults: probes, resource limits, non-root, NetworkPolicy |
| `prompts/dockerfile-review.prompt.md` | Review a Dockerfile against build-speed + security best practices |

## Why the flagship prompt is so long

"Generate a production-ready REST API" leaves Copilot guessing at the ~10 decisions
that make code enterprise-grade: auth model, authorization granularity, validation,
error contract, idempotency, rate limiting, audit trail, observability, test depth,
migration strategy. The flagship prompt makes each one explicit — that is the entire
difference between demo code and mergeable code. Use it as the template when writing
flagship prompts for your other resource types.

## Reference repos worth pinning

Point Copilot's Reference lines at real implementations, not descriptions:

- [spring-projects/spring-petclinic](https://github.com/spring-projects/spring-petclinic) — the canonical layered Spring app
- [spring-projects/spring-modulith](https://github.com/spring-projects/spring-modulith) — enforced module boundaries in a monolith
- Your own best service — the strongest reference is always in-house; name it in
  `copilot-instructions.md`.
