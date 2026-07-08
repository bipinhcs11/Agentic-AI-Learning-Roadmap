package com.benefits.mcp;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;
import io.modelcontextprotocol.client.McpClient;
import io.modelcontextprotocol.client.McpSyncClient;
import io.modelcontextprotocol.client.transport.ServerParameters;
import io.modelcontextprotocol.client.transport.StdioClientTransport;
import io.modelcontextprotocol.spec.McpSchema;
import io.modelcontextprotocol.spec.McpSchema.CallToolRequest;
import io.modelcontextprotocol.spec.McpSchema.CallToolResult;
import io.modelcontextprotocol.spec.McpSchema.Content;
import io.modelcontextprotocol.spec.McpSchema.GetPromptRequest;
import io.modelcontextprotocol.spec.McpSchema.GetPromptResult;
import io.modelcontextprotocol.spec.McpSchema.InitializeResult;
import io.modelcontextprotocol.spec.McpSchema.ListPromptsResult;
import io.modelcontextprotocol.spec.McpSchema.ListResourcesResult;
import io.modelcontextprotocol.spec.McpSchema.ListToolsResult;
import io.modelcontextprotocol.spec.McpSchema.ReadResourceRequest;
import io.modelcontextprotocol.spec.McpSchema.ReadResourceResult;
import io.modelcontextprotocol.spec.McpSchema.TextContent;
import io.modelcontextprotocol.spec.McpSchema.TextResourceContents;

import java.net.URL;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.List;
import java.util.Map;

/**
 * DemoClient — A Java MCP client that launches the BenefitsMcpServer over
 * stdio and exercises every capability exposed by the server: tools,
 * resources, and prompts.
 *
 * <p>This is the Java equivalent of the Python {@code demo_client.py} used in
 * Phase 9 · Module 04 of the Agentic AI Learning Roadmap.</p>
 */
public class DemoClient {

    // ── pretty-printer shared across all helper methods ──────────────────
    private static final ObjectMapper MAPPER = new ObjectMapper()
            .enable(SerializationFeature.INDENT_OUTPUT);

    // ── banner constants ─────────────────────────────────────────────────
    private static final String BANNER = """
            ╔══════════════════════════════════════════════════════════════════════════════╗
            ║  Phase 9 · Module 04 | DemoClient.java                                     ║
            ║  MCP client that launches BenefitsMcpServer over stdio.                     ║
            ╚══════════════════════════════════════════════════════════════════════════════╝
            """;

    // ── entry point ──────────────────────────────────────────────────────

    public static void main(String[] args) {
        System.out.println(BANNER);

        // 1. Resolve the fat-JAR path from this class's own code-source.
        String jarPath = resolveJarPath();
        System.out.println("▶ Server JAR: " + jarPath);

        // 2. Build ServerParameters → StdioClientTransport → McpSyncClient
        ServerParameters serverParams = ServerParameters
                .builder("java")
                .args("-Dorg.slf4j.simpleLogger.logFile=System.err",
                      "-cp", jarPath,
                      "com.benefits.mcp.BenefitsMcpServer")
                .build();

        StdioClientTransport transport = new StdioClientTransport(serverParams);
        McpSyncClient client = McpClient.sync(transport).build();

        try {
            // 3. Initialize the MCP session
            InitializeResult initResult = client.initialize();
            System.out.println("✔ Session initialized.\n");

            // 4. List capabilities
            listTools(client);
            listResources(client);
            listPrompts(client);

            // 5. Call tools (same arguments as the Python demo)
            callTool(client, "get_employee_profile",         Map.of());
            callTool(client, "calculate_primary_contribution_match",         Map.of());
            callTool(client, "estimate_annual_primary_contribution",
                                                             Map.of("employee_contribution_percent", 10));
            callTool(client, "estimate_savings_account_adjustment",     Map.of());
            callTool(client, "search_plan_rules",            Map.of("query", "vesting employer match"));
            callTool(client, "get_plan_document",            Map.of("document_id", "savings_account_plan_summary"));

            // 6. Read resources
            readResource(client, "benefits://employee/profile");
            readResource(client, "benefits://documents/benefits-faq");

            System.out.println("\n══════════════════════════════════════════════════════════════════════════════");
            System.out.println("  All demonstrations complete.");
            System.out.println("══════════════════════════════════════════════════════════════════════════════");

        } catch (Exception ex) {
            System.err.println("❌ Error during demo: " + ex.getMessage());
            ex.printStackTrace();
        } finally {
            // 8. Graceful shutdown
            boolean closed = client.closeGracefully();
            System.out.println("▶ Client closed gracefully: " + closed);
        }
    }

    // ── JAR resolution ───────────────────────────────────────────────────

    /**
     * Resolves the path of the fat JAR that contains this class.  When
     * running from {@code java -jar}, the code-source URL points directly
     * at the JAR file.
     */
    private static String resolveJarPath() {
        try {
            URL location = DemoClient.class
                    .getProtectionDomain()
                    .getCodeSource()
                    .getLocation();
            Path path = Paths.get(location.toURI());
            return path.toAbsolutePath().toString();
        } catch (Exception e) {
            // Fallback: assume we are in the build output directory and
            // the fat JAR sits in target/.
            System.err.println("⚠ Could not resolve JAR path from code source; "
                    + "falling back to 'target/' scan: " + e.getMessage());
            return "target/benefits-mcp-server.jar";
        }
    }

    // ── listing helpers ──────────────────────────────────────────────────

    private static void listTools(McpSyncClient client) throws Exception {
        ListToolsResult result = client.listTools();
        List<McpSchema.Tool> tools = result.tools();

        printSection("TOOLS (" + tools.size() + ")");
        for (McpSchema.Tool tool : tools) {
            System.out.println("  • " + tool.name());
            System.out.println("    " + tool.description());
        }
        System.out.println();
    }

    private static void listResources(McpSyncClient client) throws Exception {
        ListResourcesResult result = client.listResources();
        List<McpSchema.Resource> resources = result.resources();

        printSection("RESOURCES (" + resources.size() + ")");
        for (McpSchema.Resource resource : resources) {
            System.out.println("  • " + resource.uri() + "  —  " + resource.name());
        }
        System.out.println();
    }

    private static void listPrompts(McpSyncClient client) throws Exception {
        ListPromptsResult result = client.listPrompts();
        List<McpSchema.Prompt> prompts = result.prompts();

        printSection("PROMPTS (" + prompts.size() + ")");
        for (McpSchema.Prompt prompt : prompts) {
            System.out.println("  • " + prompt.name());
            System.out.println("    " + prompt.description());
        }
        System.out.println();
    }

    // ── tool invocation ──────────────────────────────────────────────────

    private static void callTool(McpSyncClient client,
                                 String toolName,
                                 Map<String, Object> arguments) throws Exception {
        printSection("CALL TOOL: " + toolName);
        System.out.println("  args = " + arguments);

        CallToolResult result = client.callTool(new CallToolRequest(toolName, arguments));
        List<Content> contents = result.content();

        for (Content content : contents) {
            if (content instanceof TextContent textContent) {
                prettyPrintJson("  ", textContent.text());
            } else {
                System.out.println("  [non-text content: " + content.getClass().getSimpleName() + "]");
            }
        }
        System.out.println();
    }

    // ── resource reading ─────────────────────────────────────────────────

    private static void readResource(McpSyncClient client, String uri) throws Exception {
        printSection("READ RESOURCE: " + uri);

        ReadResourceResult result = client.readResource(new ReadResourceRequest(uri));
        List<McpSchema.ResourceContents> contents = result.contents();

        for (McpSchema.ResourceContents rc : contents) {
            if (rc instanceof TextResourceContents textRc) {
                prettyPrintJson("  ", textRc.text());
            } else {
                System.out.println("  [non-text resource: " + rc.getClass().getSimpleName() + "]");
            }
        }
        System.out.println();
    }

    // ── formatting utilities ─────────────────────────────────────────────

    private static void printSection(String title) {
        System.out.println("┌──────────────────────────────────────────────────────────────────────────────");
        System.out.println("│ " + title);
        System.out.println("└──────────────────────────────────────────────────────────────────────────────");
    }

    /**
     * Attempts to pretty-print a JSON string.  Falls back to raw output
     * when the text is not valid JSON.
     */
    private static void prettyPrintJson(String indent, String text) {
        try {
            Object json = MAPPER.readValue(text, Object.class);
            String pretty = MAPPER.writeValueAsString(json);
            for (String line : pretty.split("\n")) {
                System.out.println(indent + line);
            }
        } catch (Exception e) {
            // Not JSON — print as-is, preserving embedded newlines.
            for (String line : text.split("\n")) {
                System.out.println(indent + line);
            }
        }
    }
}
