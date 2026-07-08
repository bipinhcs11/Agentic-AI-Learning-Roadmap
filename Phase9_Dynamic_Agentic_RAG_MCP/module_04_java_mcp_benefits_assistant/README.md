# Module 04 — Java MCP Benefits Assistant

Java port of the Python [Module 01](../module_01_mcp_benefits_assistant/) MCP
Benefits Assistant. Same mock primary contribution and savings account data, same tools, same resources,
same prompt — now built with the **official MCP Java SDK**.

## Goal

Learn **Model Context Protocol (MCP)** using Java. This module mirrors
Module 01 feature-for-feature so you can compare the Python and Java
implementations side by side while focusing on MCP concepts rather than
language differences.

```text
Am I getting the full primary contribution employer match?
How much more would I contribute if I increased my primary contribution rate to 10%?
What are my estimated savings account adjustment savings?
```

All data is fictional. No real professional accounts, record system systems, benefits
providers, or employee records are used.

## Prerequisites

- **Java 17+** (tested with OpenJDK 21)
- **Maven 3.8+** (tested with 3.9.15)

## Files

| File | Purpose |
|---|---|
| `pom.xml` | Maven POM with MCP Java SDK dependency and fat-JAR packaging |
| `BenefitsMcpServer.java` | Java MCP server with 9 tools, 4 resources, and 1 prompt |
| `DemoClient.java` | MCP client that launches the server over stdio and calls tools |
| `README.md` | This file |

## Build

```bash
cd Phase9_Dynamic_Agentic_RAG_MCP/module_04_java_mcp_benefits_assistant
mvn clean package -q
```

This produces a fat JAR at:
```
target/benefits-mcp-java-1.0.0-jar-with-deps.jar
```

## Run the Demo Client

The demo client launches the MCP server as a subprocess over stdio, then calls
every tool and reads every resource — just like the Python `demo_client.py`.

```bash
java -Dorg.slf4j.simpleLogger.logFile=System.err \
     -cp target/benefits-mcp-java-1.0.0-jar-with-deps.jar \
     com.benefits.mcp.DemoClient
```

## Run the Server Standalone

The server speaks MCP over stdio and waits for a client to connect:

```bash
java -jar target/benefits-mcp-java-1.0.0-jar-with-deps.jar
```

## MCP Tools

| Tool | Purpose |
|---|---|
| `get_employee_profile` | Return mock age, salary, filing status, and adjustment assumptions |
| `get_primary_contribution_summary` | Return mock primary contribution plan and contribution details |
| `calculate_primary_contribution_match` | Estimate whether the mock employee gets the full employer match |
| `estimate_annual_primary_contribution` | Estimate annual contribution and remaining mock limit |
| `get_savings_account_summary` | Return mock savings account coverage, election, and contribution details |
| `estimate_savings_account_adjustment` | Estimate savings account adjustment savings using mock adjustment assumptions |
| `list_plan_documents` | List small built-in mock plan documents |
| `get_plan_document` | Return the full text of a mock plan document by id |
| `search_plan_rules` | Keyword search mock plan rules without RAG |

## MCP Resources

| Resource URI | Purpose |
|---|---|
| `benefits://employee/profile` | Mock employee profile |
| `benefits://primary-contribution/plan-summary` | Mock primary contribution plan summary |
| `benefits://savings-account/plan-summary` | Mock savings account plan summary |
| `benefits://documents/benefits-faq` | Mock benefits FAQ |

## MCP Prompts

| Prompt | Purpose |
|---|---|
| `benefits_question_prompt` | Safe prompt template for educational benefits questions |

## Connect to Claude Desktop

Add a server entry to your Claude Desktop MCP config. Adjust the absolute path
for your machine:

```json
{
  "mcpServers": {
    "mock-benefits-assistant-java": {
      "command": "java",
      "args": [
        "-Dorg.slf4j.simpleLogger.logFile=System.err",
        "-jar",
        "/Users/bipinpradhan/Documents/Agentic AI learning Roadmap/Phase9_Dynamic_Agentic_RAG_MCP/module_04_java_mcp_benefits_assistant/target/benefits-mcp-java-1.0.0-jar-with-deps.jar"
      ]
    }
  }
}
```

Restart Claude Desktop after editing the config. Then ask:

```text
Using the mock benefits assistant, am I getting the full primary contribution match?
```

## Technology Stack

| Component | Choice |
|---|---|
| SDK | `io.modelcontextprotocol.sdk:mcp` 0.10.0 (official MCP Java SDK) |
| Transport | Stdio (stdin/stdout JSON-RPC) |
| Build | Maven with `maven-assembly-plugin` for fat JAR |
| Java | 17+ target (builds and runs on 21) |

## Python vs Java Comparison

| Aspect | Python (Module 01) | Java (Module 04) |
|---|---|---|
| SDK | `mcp` (FastMCP) | `io.modelcontextprotocol.sdk:mcp` |
| Server code | `benefits_mcp_server.py` (353 lines) | `BenefitsMcpServer.java` (~370 lines) |
| Client code | `demo_client.py` (98 lines) | `DemoClient.java` (~235 lines) |
| Transport | stdio | stdio |
| Tool registration | `@mcp.tool()` decorator | `SyncToolSpecification` record + builder |
| Resource registration | `@mcp.resource(uri)` decorator | `SyncResourceSpecification` record + builder |
| Prompt registration | `@mcp.prompt()` decorator | `SyncPromptSpecification` record + builder |
| Run command | `python benefits_mcp_server.py` | `java -jar <fat-jar>.jar` |
| Dependencies | `pip install mcp` | Maven (auto-downloads) |

The Python `FastMCP` API uses decorators for a concise feel. The Java SDK uses
explicit builder patterns and record types, which is more verbose but gives
you full IDE autocomplete and type safety.

## Educational Safety Note

This module is for learning MCP only. It is not professional, adjustment, legal, or
allocation advice. The data, limits, formulas, rates, and employer plan details
are mock examples. Real benefits decisions should be checked against official
plan documents and qualified professionals.
