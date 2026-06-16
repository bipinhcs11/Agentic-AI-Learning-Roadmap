# Module 05 — Spring Boot MCP + RAG Benefits Microservice

This module takes the same mock 401(k)/HSA learning domain and shows how it
looks in an enterprise Java/Spring Boot shape:

- Spring Boot WebMVC microservice
- Spring AI MCP server annotations
- Streamable HTTP MCP endpoint
- REST endpoints for developer inspection
- lightweight in-memory RAG over bundled markdown reference summaries
- recording-friendly Agent Playground UI for LinkedIn/video demos

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

Browser demo
  -> Agent Playground (/)
      -> deterministic demo router (/api/benefits/agent/ask)
          -> MCP-style account tools + RAG retrieval trace
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
| UI | Static Agent Playground served by Spring Boot at `/` |

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

Open the recording UI:

```text
http://localhost:8085/
```

The UI includes a backend switcher:

| Backend | API |
|---|---|
| Python MCP + RAG | `http://localhost:8090/api/benefits/agent/ask` |
| Spring Boot MCP + RAG | `http://localhost:8085/api/benefits/agent/ask` |

Start Module 02's `python demo_api.py` if you want the same screen to call the
Python backend during recording.

```bash
curl "http://localhost:8085/api/benefits/profile"
curl "http://localhost:8085/api/benefits/rag/search?query=2026%20HSA%20family%20limit"
curl -X POST "http://localhost:8085/api/benefits/401k/match" \
  -H "Content-Type: application/json" \
  -d '{"salary":120000,"employeeContributionPercent":6}'
curl -X POST "http://localhost:8085/api/benefits/agent/ask" \
  -H "Content-Type: application/json" \
  -d '{"question":"I contribute 6% to my 401(k). Am I getting the full match, and what is the 2026 employee limit?"}'
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
| `POST /api/benefits/agent/ask` | Recording-friendly route, tool trace, RAG hits, answer, and citations |

## Record The UI Demo

Use this module as the main Module 04 + 05 LinkedIn/video story:

```text
Plain Java proves MCP is language-agnostic.
Spring Boot shows how the same idea becomes a microservice.
```

Recommended capture flow:

1. Open `http://localhost:8085/`.
2. Select the Spring Boot backend for Module 05 or the Python backend for Module 02.
3. Run the default MCP + RAG prompt.
4. Show the route badge, tool calls, retrieved documents, and final answer.
5. Cut briefly to the debug panel or an MCP inspector pointed at `http://localhost:8085/mcp`.
6. Return to the UI and switch between the MCP, RAG, and Direct sample prompts.

## Learning Notes

This module is deliberately not a full production system:

- no database
- no tenant auth
- no real payroll, HSA, 401(k), or HR integrations
- no vector database
- no cloud deployment

Those are capstone or later-phase concerns. The goal here is to make the MCP +
RAG microservice shape familiar to Spring Boot developers.
