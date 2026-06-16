# Demo Recordings

This folder keeps lightweight terminal transcripts for demos that are useful to
review without rerunning a local server.

These are text recordings, not binary videos, so they are small enough to keep
in git and easy to diff.

| File | Demo |
|---|---|
| `module04_java_mcp_demo_terminal.txt` | Java MCP client launching the Java MCP server over stdio and exercising tools, resources, and prompts |

## Preferred Phase 9 Video Surface

For the Python and Spring Boot LinkedIn posts, use the same Agent Playground UI.
This keeps the visual language consistent while the backend changes.

Python Module 02 backend:

```text
cd ../module_02_mcp_rag_enterprise_integration
python demo_api.py
```

Then open:

```text
http://localhost:8090/
```

Spring Boot Module 05 backend:

```text
cd ../module_05_springboot_mcp_benefits_assistant
mvn spring-boot:run
```

Then open:

```text
http://localhost:8085/
```

Either UI can switch between the Python API on `8090` and the Spring Boot API on
`8085`. Use the UI as the main video and keep the MCP inspector or terminal logs
as a short technical cutaway. The story is: Python teaches the MCP + RAG routing
pattern; plain Java proves MCP is language agnostic; Spring Boot makes it
service-ready.
