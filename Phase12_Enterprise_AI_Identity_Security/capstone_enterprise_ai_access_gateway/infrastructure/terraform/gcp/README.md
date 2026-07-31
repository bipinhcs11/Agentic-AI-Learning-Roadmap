# Google Cloud Live Deployment Track

This track deploys the Phase 12 security contract to a dedicated Google Cloud
project. Its Terraform foundation and mock tests are implemented. No Google
Cloud plan or apply has been run with real credentials.

## Implemented foundation

- mandatory billing-account budget filtered to the sandbox project
- required API enablement and Artifact Registry cleanup policies
- separate service accounts for all four services and three fictional agents
- empty Secret Manager containers, with no secret material in Terraform
- GitHub Workload Identity Federation restricted by immutable owner ID,
  repository, and branch
- optional Cloud Run services gated by four immutable image digests
- only the gateway receives `allUsers`; internal invoker roles are limited to
  the gateway service account
- Terraform tests for safe defaults, rejected mutable inputs, and IAM shape

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

## Validate without Google credentials

```bash
terraform init -backend=false
terraform validate
terraform test
```

The safe default creates no Cloud Run services in the mock plan. Copy
`terraform.tfvars.example`, replace the project, billing account, and immutable
GitHub owner ID, publish all four digest-addressed images, and review the real
plan before setting `enable_runtime = true`.

## Remaining live work

- wire authenticated internal service URLs and ID-token audiences
- add Cloud SQL, revocation cache, KMS signing, and secret versions
- restrict network ingress further after validating Cloud Run service-to-service routing
- run the shared denial, trace-correlation, and Cloud Asset teardown suite

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
