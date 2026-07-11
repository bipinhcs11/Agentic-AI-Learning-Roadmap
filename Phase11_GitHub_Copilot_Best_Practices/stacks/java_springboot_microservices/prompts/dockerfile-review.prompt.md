---
mode: ask
description: "Review a Dockerfile for security, size, and build-cache correctness"
---

# /dockerfile-review

**Role**: You review container images the way a supply-chain security team does:
every layer is attack surface, every cache miss is money.

**Context**: Review ${file}. This image runs on an enterprise cluster where root
containers are blocked by admission policy and images are pulled through an internal
registry proxy.

**Task**: Review against, in order:
1. **Base image** — pinned by digest (not `latest`), from the approved internal
   registry, minimal variant (distroless/alpine/slim where the runtime allows).
2. **Multi-stage** — build tools never present in the final image; final stage copies
   artifacts only.
3. **User** — explicit non-root USER; writable paths declared, everything else
   read-only.
4. **Secrets** — no ARG/ENV secrets, no credential files COPYed in, no secret reachable
   in any intermediate layer.
5. **Cache order** — dependency manifests copied and resolved before source, so code
   changes don't re-download the world.
6. **Runtime hygiene (JVM)** — container-aware memory flags, proper signal handling
   (exec-form ENTRYPOINT, no shell-wrapped PID 1), tini/dumb-init if needed.
7. **Metadata** — OCI labels for source/version; HEALTHCHECK only if the platform
   doesn't already probe.

**Constraints**: findings ranked by severity with the exact line quoted and the exact
replacement line proposed. If the file is already correct on a point, say "pass" —
the checklist result must be complete either way, so the review is auditable.

**Output**: Findings table (severity, line, issue, fix), then the fully corrected
Dockerfile in one block.

**Reference**: `.github/instructions/security.instructions.md`.
