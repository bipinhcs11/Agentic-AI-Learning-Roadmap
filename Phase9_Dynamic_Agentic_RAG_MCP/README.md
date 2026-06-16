# Phase 9 — Dynamic Agentic RAG + MCP

Phase 9 adds a focused MCP learning track after the original eight-phase
roadmap. The goal is to learn **Model Context Protocol (MCP)** first, then
combine MCP with RAG, and finally ship the pattern as an enterprise-style
capstone.

## Modules

| # | Module | What You Build | Status |
|---|---|---|---|
| 01 | MCP Benefits Assistant | Local MCP server for mock 401(k) + HSA tools/resources | Built |
| 02 | MCP + RAG Enterprise Integration | Structured MCP tools plus document-grounded RAG | Built |
| 03 | Enterprise Assistant Hub Capstone | Multi-tenant MCP gateway + RAG + AWS provider abstraction | Built |
| 04 | Java MCP Benefits Assistant | Plain Java version of Module 01 for side-by-side comparison | Built |
| 05 | Spring Boot MCP + RAG Benefits Microservice | Spring WebMVC + MCP Streamable HTTP + lightweight RAG + demo UI | Built |

## Progression

```text
Module 01: Learn MCP with mock 401(k)/HSA tools and resources
    ↓
Module 02: Add RAG over benefits and policy documents
    ↓
Capstone: Turn MCP + RAG into an enterprise assistant platform
    ↓
Java/Spring variants: show the same ideas for enterprise Java teams
```

For LinkedIn/video demos, treat Modules 04 and 05 as one JVM story: Module 04
proves MCP is language-agnostic with the plain Java SDK, and Module 05 becomes
the main JVM recording surface with the Spring Boot Agent Playground UI. Module
02 also exposes a Python demo API on port `8090`, so the same Agent Playground
visual style can be used for both the Python MCP + RAG post and the Spring Boot
post.

## Why Start With Benefits?

401(k) and HSA questions are a good teaching domain because they naturally mix:

- structured account/profile data
- plan rules and policy text
- calculations
- careful safety boundaries
- enterprise integration patterns

The examples use mock data only. They are educational and are not financial,
tax, legal, or investment advice.

## Existing Prototype

`mcp_benefits_example/` is an earlier MCP+RAG prototype that uses a retrieval
tool over local 401(k)/HSA markdown reference docs. Keep it as a reference for
the later MCP + RAG modules while Module 01 remains intentionally MCP-only.
