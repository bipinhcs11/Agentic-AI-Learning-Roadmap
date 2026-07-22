# Module 07 — AWS Bedrock AgentCore Identity

This optional module maps the local Phase 12 model to Amazon Bedrock AgentCore
Identity. The core labs do not require an AWS account.

## Concept mapping

| Phase 12 concept | AWS mapping |
|---|---|
| Running agent principal | AgentCore workload identity |
| Workload credential | workload access token |
| User on whose behalf the agent acts | user identity carried with the workload access context |
| Outbound tool credential | credential provider backed by the token vault |
| Protected inbound call | inbound JWT authorizer |
| Scope reduction | IAM policy plus workload-identity restriction on credential providers |
| Lifecycle and audit | AgentCore identity directory, IAM controls, and AWS audit services |

AgentCore workload identities are a stable identity anchor for hosted or custom
agents. They can authorize access to credential providers without embedding a
third-party API key in the agent process.

## Offline design exercise

```bash
python3 ../docs/validate_provider_mapping.py provider-mapping.json
```

Expected output:

```text
VALID: provider-mapping.json
```

Review the manifest and answer:

1. Which identity represents the running Finance agent?
2. Where is an outbound OAuth credential stored?
3. Which policy prevents the Email agent from using the Finance provider?
4. Which user and task identifiers must be copied into application audit data?

## Optional live lab

Use a dedicated sandbox AWS account and the current official AgentCore Identity
guide to:

1. Create or deploy an agent workload identity.
2. Configure inbound JWT authentication for the agent or gateway.
3. Configure one fictional OAuth credential provider.
4. Restrict provider access to the intended workload identity.
5. Obtain a workload access token and a short-lived outbound credential.
6. Verify the Email agent identity cannot access the Finance provider.
7. Delete all sandbox identities, providers, and stored credentials.

Do not paste cloud credentials into this repository or terminal transcripts.
CLI and SDK commands are intentionally linked rather than copied because the
AgentCore surface is evolving.

## Official references

- [AgentCore Identity overview](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/identity.html)
- [Understanding workload identities](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/understanding-agent-identities.html)
- [Obtaining credentials](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/obtain-credentials.html)
