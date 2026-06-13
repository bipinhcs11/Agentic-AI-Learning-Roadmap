# Phase 9 — Dynamic Agentic RAG + MCP

This phase is about the **Model Context Protocol (MCP)**: exposing tools,
resources, prompts, and retrieval endpoints to an LLM so the system can choose
the right context path at runtime.

The learning sequence is intentionally staged:

```text
Pure MCP
  -> MCP + RAG
  -> Enterprise capstone
  -> Java/Spring Boot variants for enterprise teams
```

## Module 01 — MCP Benefits Assistant  ✅ built

`module_01_mcp_benefits_assistant/` is the first clean MCP exercise.

Goal:
Build a local MCP server that teaches how MCP tools and resources work before
integrating MCP with RAG in later modules or the Phase 8 capstone upgrade.

Original brainstorm location:
`Phase8_Integrations_Shipping/project_07_mcp_benefits_assistant`

Final roadmap location:
`Phase9_Dynamic_Agentic_RAG_MCP/module_01_mcp_benefits_assistant`

Requirements captured:

- Create a Python MCP server named `benefits_mcp_server.py`.
- Use mock employee benefits data only.
- Do not require real financial accounts or credentials.
- Add MCP tools:
  - `get_employee_profile`
  - `get_401k_summary`
  - `calculate_401k_match`
  - `estimate_annual_401k_contribution`
  - `get_hsa_summary`
  - `estimate_hsa_tax_savings`
  - `list_plan_documents`
  - `search_plan_rules`
- Add MCP resources for:
  - employee profile
  - 401k plan summary
  - HSA plan summary
  - benefits FAQ
- Add a simple client/demo script showing example prompts and tool calls.
- Add beginner-friendly docs explaining:
  - what MCP is
  - why 401(k) + HSA is a good MCP example
  - how to run the server
  - how to connect it to Claude Desktop or Claude Code
  - how this later combines with RAG
- Keep all guidance educational.
- Add a note that this is not financial, tax, legal, or investment advice.
- Do not integrate with AWS yet.
- Do not add RAG yet.
- Include a section called “Next Step: MCP + RAG”.

## Module 02 — MCP + RAG Enterprise Integration  ✅ built

`module_02_mcp_rag_enterprise_integration/` combines MCP tools with RAG over
public-source benefits reference summaries and mock account tools.

Dynamic flow:

```text
User question
  -> call MCP tools for structured employee/plan data
  -> run RAG over policy docs when document context is needed
  -> combine tool output + citations
  -> answer with educational safety boundaries
```

The older `mcp_benefits_example/` folder is an early working MCP+RAG prototype
and can be used as a reference when building this module.

Retrieval uses heading-anchored chunks, Ollama `nomic-embed-text`, NumPy cosine,
topic/keyword reranking, and a small 401(k) intent boost so an employee
salary-deferral limit query ranks the $24,500 employee-only limit above the
$72,000 combined employee plus employer cap.

## Capstone — Enterprise Assistant Hub  ✅ built

`capstone_enterprise_assistant_hub/` is the production-style Phase 9 capstone.
It intentionally stays smaller than the Phase 8 SaaS app while reusing its
patterns:

- cloud LLM provider abstraction with `AI_PROVIDER=ollama|bedrock|sagemaker|hf`
- tenant config with API-key-to-tenant mapping, allowed tools, and per-tenant corpus
- MCP gateway that can load the Module 02 benefits server through
  `langchain-mcp-adapters` and enforces tenant allowlists before tool execution
- tenant-scoped RAG with the corrected Module 02 reranker
- dynamic route selection for `direct`, `mcp_only`, `rag_only`, and `mcp+rag`
- CLI entrypoint: `python hub.py --tenant acme "question"`
- thin FastAPI `/chat` endpoint using mock API keys
- structured JSONL audit log with route, tools, docs, provider, and token counts

Skipped by design: Slack, observability, real AWS deploy, billing, and the full
Phase 8 auth model. Those stay in Phase 8; this capstone focuses on the MCP/RAG
enterprise integration boundary.

## Module 04 — Java MCP Benefits Assistant  ✅ built

`module_04_java_mcp_benefits_assistant/` is the plain Java companion to Module
01. It should stay close to the Python module: same mock 401(k)/HSA domain, same
tools/resources/prompts, and the same safety boundaries. The point is
side-by-side comparison for Java developers, not a new product surface. The demo
client launches the Java server over stdio and exercises tools, resources, and
prompts; a terminal transcript lives in `demo_recordings/`.

## Module 05 — Spring Boot MCP + RAG Benefits Microservice  ✅ built

`module_05_springboot_mcp_benefits_assistant/` shows the same MCP + RAG pattern
in a Spring Boot WebMVC microservice shape:

- Spring AI MCP server annotations
- Streamable HTTP MCP endpoint at `/mcp`
- REST inspection endpoints under `/api/benefits`
- mock benefits account tools
- lightweight in-memory RAG over bundled markdown reference summaries
- regression test for ranking the 2026 employee 401(k) limit above the combined
  employee plus employer cap

This still belongs in Phase 9. A future Phase 10 should wait until the Java and
Spring variants are stable enough to justify a broader theme such as polyglot
production agents, Kubernetes deployment, or enterprise governance.

## Related Phase 8 Upgrade Spec

The Phase 8 capstone upgrade spec still matters, but it should come after the
Phase 9 learning modules:

`../Phase8_Integrations_Shipping/project_06_capstone_launch/UPGRADE_SPEC_dynamic_providers_mcp.md`

---

*Note: the empty `common/` and `project_01...05/` folders are leftover
scaffolding from an earlier draft and can be deleted later.*
