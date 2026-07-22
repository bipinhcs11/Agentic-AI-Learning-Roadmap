# Google Cloud Live Deployment Track

This track deploys the Phase 12 security contract to a dedicated Google Cloud
project. It is a specification until its Terraform and automated tests are
added.

## Target mapping

| Phase 12 responsibility | Google Cloud target |
|---|---|
| Agent and service execution | Cloud Run |
| Workload identity | Dedicated IAM service account per runtime service |
| External and CI identity | Workload Identity Federation |
| Container images | Artifact Registry with immutable digest deployment |
| Durable identity data | Cloud SQL for PostgreSQL |
| Task and revocation state | Memorystore or another managed Redis-compatible cache |
| Secrets and signing keys | Secret Manager and Cloud KMS |
| Policy and MCP services | Authenticated, ingress-restricted Cloud Run services |
| Audit and traces | Cloud Audit Logs, Cloud Logging, Trace, and OpenTelemetry |
| Keyless CI/CD | GitHub OIDC through a restricted workload identity provider |

Use Workload Identity Federation rather than downloading a service-account key.
Attribute conditions must restrict the repository, owner, branch or protected
environment, and expected token audience.

## Required demonstrations

- Every Cloud Run service uses its own least-privilege service account.
- Only the gateway permits intended public ingress; internal services require
  authenticated service-to-service invocation.
- The deployment pipeline exchanges an OIDC assertion for short-lived Google
  credentials and stores no service-account key.
- Cross-tenant, wrong-audience, excessive-scope, and revoked-task requests are
  denied after deployment.
- Cloud Audit Logs and application traces correlate the same fictional
  `audit_id` without retaining raw JWTs.
- Asset inventory finds no project resources created by the lab after teardown.

## References

- [Workload Identity Federation](https://cloud.google.com/iam/docs/workload-identity-federation)
- [Workload identities](https://cloud.google.com/iam/docs/workload-identities)
- [Workload Identity Federation security practices](https://cloud.google.com/iam/docs/best-practices-for-using-workload-identity-federation)
