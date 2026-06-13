# Module 05 — Spring Boot MCP + RAG Benefits Microservice

This module takes the same mock 401(k)/HSA learning domain and shows how it
looks in an enterprise Java/Spring Boot shape:

- Spring Boot WebMVC microservice
- Spring AI MCP server annotations
- Streamable HTTP MCP endpoint
- REST endpoints for developer inspection
- lightweight in-memory RAG over bundled markdown reference summaries

All data is fictional. This is educational only and is not financial, tax,
legal, or investment advice.

## Why This Is Module 05, Not Phase 10

This still belongs in Phase 9 because the core lesson is MCP + RAG. The new
dimension is runtime style: Python first, plain Java next, then Spring Boot for
microservice developers. A future Phase 10 can be broader once these patterns
are proven, for example polyglot production agents, Kubernetes deployment, or
enterprise governance.

## Architecture

```text
MCP client or agent
  -> Streamable HTTP MCP endpoint (/mcp)
      -> Spring AI MCP annotated tools/resources/prompts
          -> mock account service
          -> in-memory benefits RAG service

Developer/browser/curl
  -> REST endpoints (/api/benefits/*)
      -> same mock account + RAG services
```

## What You Build

| Layer | Implementation |
|---|---|
| MCP server | Spring AI `spring-ai-starter-mcp-server-webmvc` |
| MCP transport | Streamable HTTP at `/mcp` |
| MCP tools | 9 annotated `@McpTool` methods |
| MCP resources | 4 annotated `@McpResource` handlers |
| MCP prompt | 1 safe benefits question `@McpPrompt` |
| RAG | Heading-anchored markdown chunks + lexical/topic/intent rerank |
| REST | `/api/benefits/*` endpoints over the same service layer |

This module follows the Spring AI MCP server starter and annotation model from
the official Spring AI docs:

- https://docs.spring.io/spring-ai/reference/api/mcp/mcp-server-boot-starter-docs.html
- https://docs.spring.io/spring-ai/reference/api/mcp/mcp-annotations-server.html

## Prerequisites

- Java 17+
- Maven 3.8+

Tested locally with Java 21 and Maven 3.9.

## Run Tests

```bash
cd Phase9_Dynamic_Agentic_RAG_MCP/module_05_springboot_mcp_benefits_assistant
mvn test
```

The tests verify:

- 401(k) match calculation
- HSA tax savings calculation
- HSA limit retrieval
- employee 401(k) contribution-limit ranking above the combined $72,000 cap
- Spring Boot application context and MCP auto-registration

## Run The Microservice

```bash
mvn spring-boot:run
```

Default port: `8085`

```bash
curl "http://localhost:8085/api/benefits/profile"
curl "http://localhost:8085/api/benefits/rag/search?query=2026%20HSA%20family%20limit"
curl -X POST "http://localhost:8085/api/benefits/401k/match" \
  -H "Content-Type: application/json" \
  -d '{"salary":120000,"employeeContributionPercent":6}'
```

The MCP Streamable HTTP endpoint is:

```text
http://localhost:8085/mcp
```

Use this endpoint from an MCP client that supports Streamable HTTP. For
Claude Desktop-style stdio learning, keep using Module 01/04.

## MCP Tools

| Tool | Purpose |
|---|---|
| `get_employee_profile` | Return mock employee profile |
| `get_401k_summary` | Return mock 401(k) plan and contribution summary |
| `calculate_401k_match` | Estimate mock employer match |
| `get_hsa_summary` | Return mock HSA plan summary |
| `estimate_hsa_tax_savings` | Estimate mock HSA tax savings |
| `search_benefits_docs` | Search bundled 401(k)/HSA reference summaries |
| `list_documents` | List available RAG documents |
| `get_document_excerpt` | Return a bounded document excerpt |
| `list_sources` | Return citation source URLs |

## REST Endpoints

| Endpoint | Purpose |
|---|---|
| `GET /api/benefits/profile` | Mock employee profile |
| `GET /api/benefits/401k` | Mock 401(k) summary |
| `POST /api/benefits/401k/match` | Match estimate |
| `GET /api/benefits/hsa` | Mock HSA summary |
| `GET /api/benefits/hsa/tax-savings` | HSA tax estimate |
| `GET /api/benefits/rag/search?query=...` | RAG search |
| `GET /api/benefits/documents` | Document catalog |
| `GET /api/benefits/documents/excerpt?documentId=...` | Document excerpt |
| `GET /api/benefits/sources` | Source URL catalog |

## Learning Notes

This module is deliberately not a full production system:

- no database
- no tenant auth
- no real payroll, HSA, 401(k), or HR integrations
- no vector database
- no cloud deployment

Those are capstone or later-phase concerns. The goal here is to make the MCP +
RAG microservice shape familiar to Spring Boot developers.
