# Module 09 — Google Cloud Vertex AI + IAM

Google Cloud's mapping is intentionally described as workload IAM rather than
as an exact equivalent of Entra Agent ID. An agent runtime normally uses a
service account, Workload Identity Federation principal, or managed workload
identity, with IAM roles and conditions defining access.

## Concept mapping

| Phase 12 concept | Google Cloud mapping |
|---|---|
| Agent workload | service account or federated workload principal |
| External/hybrid agent | Workload Identity Federation pool principal |
| Temporary privilege-bearing identity | service-account impersonation |
| Short-lived task credential | generated OAuth access token with bounded lifetime |
| Permission attenuation | resource-level roles, IAM Conditions, and downscoping where supported |
| Delegation evidence | caller plus impersonated service account in Cloud Audit Logs |
| Vertex execution identity | service account attached to the Vertex AI workload/runtime |

The preferred design avoids exported service-account keys. Workload Identity
Federation exchanges an external OIDC, SAML, AWS, Azure, or certificate-backed
identity for short-lived Google credentials.

## Offline design exercise

```bash
python3 ../docs/validate_provider_mapping.py provider-mapping.json
```

Model the Planner and Finance agents as separate service accounts. Grant the
Planner only permission to obtain a short-lived token for Finance, and grant
Finance only the fictional read role. Do not grant the Email service account
permission to impersonate Finance.

## Optional live lab

Use a disposable Google Cloud project with billing controls:

1. Create separate Planner, Finance, and Email service accounts.
2. Grant a minimal fictional-resource role to Finance.
3. Grant the Planner token-creation permission on Finance only.
4. Generate a short-lived Finance access token through impersonation.
5. Verify the Email identity cannot generate that token.
6. Inspect Cloud Audit Logs for caller and impersonated principal context.
7. Remove bindings, service accounts, pools, and providers created by the lab.

Do not create or download service-account JSON keys for this exercise.

## Official references

- [Identities for workloads](https://docs.cloud.google.com/iam/docs/workload-identities)
- [Workload Identity Federation](https://docs.cloud.google.com/iam/docs/workload-identity-federation)
- [Service-account credentials](https://docs.cloud.google.com/iam/docs/service-account-creds)
- [Create short-lived credentials](https://docs.cloud.google.com/iam/docs/create-short-lived-credentials-direct)
