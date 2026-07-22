# Module 08 — Microsoft Entra Agent ID

This optional module maps Phase 12 to Microsoft Entra Agent ID. It focuses on
the distinction between a reusable agent identity blueprint, tenant-local agent
identities, and the humans accountable for them.

## Concept mapping

| Phase 12 concept | Microsoft Entra mapping |
|---|---|
| Agent type/template | agent identity blueprint |
| Deployed governed agent | agent identity |
| Business accountability | sponsor |
| Technical administration | owner/manager roles |
| Autonomous agent access | app token acquired on behalf of the agent identity |
| User delegation | user token where the user is subject and agent is actor |
| Fleet-wide response | policies and disable/revoke operations applied by blueprint or identity |
| Audit | agent-specific sign-in and activity records plus application audit ID |

An Entra agent identity is a specialized service principal. It has no credential
of its own; its blueprint acquires tokens on its behalf. This is materially
different from simply giving every agent a client secret.

## Offline design exercise

```bash
python3 ../docs/validate_provider_mapping.py provider-mapping.json
```

Draw one blueprint that creates separate Finance agents for two fictional
tenants. Give each identity a sponsor and tenant-local authorization. Explain
why a multitenant blueprint does not turn the created identities into shared
cross-tenant principals.

## Optional live lab

In a non-production Entra tenant, follow the current official prerequisites and:

1. Create an agent identity blueprint.
2. Create an agent identity with an owner and sponsor.
3. Configure only the fictional read permission needed by the lab.
4. Compare autonomous and interactive/delegated token claims.
5. Inspect agent sign-in and permission information.
6. Disable the identity and confirm new access is denied.
7. Remove all lab objects.

Licensing, preview status, tenant roles, and API shapes can change. Check the
official prerequisites on the day of the exercise.

## Official references

- [Microsoft Entra Agent ID documentation](https://learn.microsoft.com/en-us/entra/agent-id/)
- [Agent identities](https://learn.microsoft.com/en-us/entra/agent-id/agent-identities)
- [Agent identity key concepts](https://learn.microsoft.com/en-us/entra/agent-id/identity-platform/key-concepts)
- [Manage agent identities](https://learn.microsoft.com/en-us/entra/agent-id/manage-agent-identities-admin)
