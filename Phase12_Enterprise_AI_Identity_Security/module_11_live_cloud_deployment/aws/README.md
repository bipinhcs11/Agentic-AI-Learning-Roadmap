# AWS Live Deployment Track

This track deploys the Phase 12 security contract to a dedicated AWS sandbox.
It is a specification until its Terraform and automated tests are added.

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

AgentCore supports workload identities and managed agent runtimes. Current AWS
guidance exposes identity management through the AWS CLI and AgentCore SDK, so
the implementation must verify Terraform coverage at build time and isolate
any required native bootstrap behind a narrow IAM policy.

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
