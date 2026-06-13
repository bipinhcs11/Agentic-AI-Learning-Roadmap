# Phase 9 — Dynamic Agentic RAG + MCP

Phase 9 adds a focused MCP learning track after the original eight-phase
roadmap. The goal is to learn **Model Context Protocol (MCP)** first, then
combine MCP with RAG, and finally ship the pattern as an enterprise-style
capstone.

## Modules

| # | Module | What You Build | Status |
|---|---|---|---|
| 01 | MCP Benefits Assistant | Local MCP server for mock 401(k) + HSA tools/resources | Built |
| 02 | MCP + RAG Enterprise Integration | Structured MCP tools plus document-grounded RAG | Planned |
| 03 | Enterprise Assistant Hub Capstone | Multi-tenant MCP gateway + RAG + AWS provider abstraction | Planned |

## Progression

```text
Module 01: Learn MCP with mock 401(k)/HSA tools and resources
    ↓
Module 02: Add RAG over benefits and policy documents
    ↓
Capstone: Turn MCP + RAG into an enterprise assistant platform
```

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
Module 02 while Module 01 remains intentionally MCP-only.
