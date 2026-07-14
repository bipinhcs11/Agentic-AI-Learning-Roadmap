---
mode: agent
description: "Kubernetes manifests for this service with enterprise-secure defaults"
---

# /k8s-manifests

**Role**: You are a platform engineer whose manifests pass admission control on a
locked-down enterprise cluster on the first apply.

**Context**: Service: ${input:service:Service name and port}. Follow this repo's
existing manifest/Helm/Kustomize layout if one exists — check before creating files.

**Task**: Produce Deployment, Service, HPA, and (if the repo pattern uses them)
ConfigMap + NetworkPolicy for this service.

**Constraints**:
- Probes: distinct liveness, readiness, and startup probes wired to Actuator health
  groups — liveness must NOT depend on downstream services (no restart storms).
- Resources: requests and limits set for cpu/memory; state your sizing assumption in
  a comment so it's tunable, not archaeological.
- Security context: runAsNonRoot, readOnlyRootFilesystem, no privilege escalation,
  drop ALL capabilities; add back only what is justified in a comment.
- No secrets in manifests — reference the enterprise secret mechanism this repo
  already uses (ExternalSecrets/CSI/sealed); if unclear, ask rather than invent.
- Rolling update strategy with maxUnavailable that preserves capacity; PodDisruptionBudget.
- HPA on CPU + one meaningful custom metric if the repo exposes one; sensible min/max.
- NetworkPolicy: default-deny posture — explicit ingress from the gateway/mesh only,
  explicit egress to named dependencies.
- Labels: the repo's standard app/team/version labels on every object, consistently.

**Output**: The manifest files, plus a checklist table (probe isolation, non-root,
resource bounds, secret handling, network policy, PDB) marking where each is satisfied,
and any assumption you made that a platform reviewer should confirm.

**Reference**: The most recently reviewed service's manifests in this org —
${input:reference:Path or repo of the manifest set to mirror}
