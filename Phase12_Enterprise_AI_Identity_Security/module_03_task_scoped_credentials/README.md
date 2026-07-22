# Module 03 — Task-Scoped Credentials

This module turns least privilege into a runnable resource-server boundary.
The fictional invoice API accepts only a signed task credential that is:

- issued by the Module 02 identity service
- intended for `fictional-invoice-api`
- granted `invoice.read`
- bound to a non-empty `task_id`
- assigned to the same tenant as the requested invoice
- associated with an agent that is still active

## Run

Start Module 02 on port `8081`, register an agent, and request a task token as
shown in its README. In another terminal:

```bash
mvn spring-boot:run
```

Use the task token:

```bash
curl -s http://localhost:8082/fictional-invoices/inv-acme-001 \
  -H "Authorization: Bearer $TASK_TOKEN"
```

Expected output shape:

```json
{
  "id":"inv-acme-001",
  "tenantId":"fictional-acme",
  "vendor":"Fictional Office Supply Co.",
  "amount":"125.00",
  "currency":"USD",
  "status":"OPEN",
  "taskId":"task-demo-001",
  "auditId":"..."
}
```

Try the same token against `inv-globex-001`; the API returns `403` even though
the signature and scope are valid. This is the deliberate tenant-isolation
test.

## Test

```bash
mvn test
```

The tests cover missing authentication, missing scope, non-task tokens,
cross-tenant access, revoked agents, and the successful narrow read.
