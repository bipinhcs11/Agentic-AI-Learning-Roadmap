# MCP Path

Use this path if you want to learn the Model Context Protocol as an integration
boundary for tools, resources, prompts, and enterprise assistant systems.

## Recommended Order

| Step | Folder | Skill |
|---:|---|---|
| 1 | `Phase9_Dynamic_Agentic_RAG_MCP/module_01_mcp_benefits_assistant/` | Build a small MCP server with tools/resources |
| 2 | `Phase9_Dynamic_Agentic_RAG_MCP/module_02_mcp_rag_enterprise_integration/` | Combine MCP tools with document retrieval |
| 3 | `Phase9_Dynamic_Agentic_RAG_MCP/capstone_enterprise_assistant_hub/` | Add tenant boundaries, route decisions, audit logs, and providers |
| 4 | `Phase9_Dynamic_Agentic_RAG_MCP/module_04_java_mcp_benefits_assistant/` | Rebuild the pattern in Java |
| 5 | `Phase9_Dynamic_Agentic_RAG_MCP/module_05_springboot_mcp_benefits_assistant/` | Add Spring Boot, REST, and Streamable HTTP MCP |

## Enterprise Patterns To Notice

- Tool allowlists are checked before execution.
- Tenant context is injected server-side.
- RAG corpora are scoped by tenant.
- Cloud provider SDKs are lazy-loaded so local tests stay light.
- Outputs are marked educational when using benefits or finance-like examples.

## Offline Test Command

```bash
cd Phase9_Dynamic_Agentic_RAG_MCP/capstone_enterprise_assistant_hub
python -m pytest -q tests
```

These tests mock cloud SDKs and do not require Ollama or AWS credentials.
