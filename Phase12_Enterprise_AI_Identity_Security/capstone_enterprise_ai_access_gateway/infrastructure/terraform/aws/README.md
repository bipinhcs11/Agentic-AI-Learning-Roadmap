# AWS Live Deployment Track

This track deploys the Phase 12 security contract to a dedicated AWS sandbox.
Its Terraform foundation and mock tests are implemented. No AWS plan or apply
has been run with real credentials.

## Implemented foundation

- mandatory AWS Budget with a learning-size upper bound
- immutable, scan-on-push ECR repositories for the three Java services
- short-retention CloudWatch log groups
- distinct native AgentCore workload identities for Planner, Finance, and Email
- minimum AgentCore runtime role for ECR image pull and MCP logs
- optional JWT-protected AgentCore MCP runtime gated by an immutable image digest
- optional GitHub OIDC role restricted to one repository and branch
- Terraform tests for safe defaults, rejected mutable inputs, and runtime shape

## Target mapping

| Phase 12 responsibility | AWS target |
|---|---|
| Agent execution | Amazon Bedrock AgentCore Runtime or isolated managed container compute |
| Agent identity | AgentCore workload identity plus least-privilege IAM execution role |
| Public entry point | TLS application gateway with JWT authentication |
| Container images | Amazon ECR with immutable tags or digest deployment |
| Durable identity data | Managed PostgreSQL |
| Task and revocation state | Managed Redis-compatible cache |
| Secrets and signing keys | AWS Secrets Manager and AWS KMS |
| Policy and MCP services | Private container services |
| Audit and traces | CloudTrail, CloudWatch, and OpenTelemetry export |
| Keyless CI/CD | GitHub OIDC to a restricted IAM deployment role |

The official AWS provider now supports AgentCore workload identities and agent
runtimes directly. This track therefore does not need a CLI bootstrap for those
objects.

## Validate without AWS credentials

```bash
terraform init -backend=false
terraform validate
terraform test
```

The safe default creates no AgentCore runtime in the mock plan. Copy
`terraform.tfvars.example`, replace its sandbox values, publish an immutable
MCP image, and set `enable_runtime = true` only after reviewing a real plan.

## Remaining live work

- add the identity gateway and policy service runtime topology
- add managed PostgreSQL, revocation state, secret versions, and KMS integration
- decide between public JWT-protected or VPC AgentCore networking after teardown
  testing; service-managed network interfaces can delay VPC cleanup
- run the shared denial, audit-correlation, and destroy inventory suite

## Required demonstrations

- Runtime code receives role credentials without environment access keys.
- AgentCore or the selected JWT authorizer validates the intended issuer and
  audience.
- Finance and Email agents use distinct identities and policies.
- Private MCP and data endpoints reject direct public access.
- CloudTrail and application telemetry correlate the same fictional `audit_id`.
- The post-destroy inventory finds no runtimes, load balancers, databases,
  caches, repositories, secret versions, or log groups created by the lab.

## References

- [AgentCore Identity](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/identity.html)
- [Create and manage AgentCore workload identities](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/creating-agent-identities.html)
- [AgentCore Runtime security practices](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-security-best-practices.html)
