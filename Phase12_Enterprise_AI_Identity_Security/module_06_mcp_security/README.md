# Module 06 — Secure MCP

This module protects a Spring Boot Streamable HTTP MCP server with the task
credentials issued in Module 02.

## Controls

- RS256 signature, issuer, time, and audience validation
- OAuth protected-resource metadata discovery
- task credentials required for MCP calls
- scope-to-tool allow-list enforced inside every tool
- tenant isolation at the fictional data lookup
- maximum delegation-depth check
- bounded, redacted audit events for allows and denials
- no tool can send email or change an invoice

| MCP tool | Required scope | Data access |
|---|---|---|
| `get_fictional_invoice` | `invoice.read` | tenant-filtered fictional invoice |
| `draft_fictional_email` | `email.draft` | creates an in-memory draft only |

Listing a tool does not authorize its use. The server repeats authorization at
invocation time, independent of any model or prompt instruction.

## Run

Start Module 02, register an agent, and request a task token whose audience is
`http://localhost:8086/mcp`. Then:

```bash
mvn spring-boot:run
```

Discover authorization metadata:

```bash
curl -s http://localhost:8086/.well-known/oauth-protected-resource
```

Initialize an MCP session:

```bash
curl -i http://localhost:8086/mcp \
  -H "Authorization: Bearer $TASK_TOKEN" \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -d '{
    "jsonrpc":"2.0",
    "id":1,
    "method":"initialize",
    "params":{
      "protocolVersion":"2025-06-18",
      "capabilities":{},
      "clientInfo":{"name":"phase12-curl","version":"1.0"}
    }
  }'
```

The response includes an `Mcp-Session-Id` header. Send it on subsequent
`tools/list` and `tools/call` requests.

## Denial exercises

Try each of these and confirm the server denies the call:

- no bearer token
- a token intended for the invoice REST API instead of this MCP resource
- `email.draft` token calling `get_fictional_invoice`
- `fictional-acme` token requesting `inv-globex-001`
- a general agent token instead of a task token
- delegation depth greater than two

## Test

```bash
mvn test
```
