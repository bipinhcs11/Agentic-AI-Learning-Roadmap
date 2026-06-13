/*
 * ╔══════════════════════════════════════════════════════════════════════════════╗
 * ║  Phase 9 · Module 04 | BenefitsMcpServer.java                              ║
 * ║  Local MCP Benefits Assistant for mock 401(k) and HSA data.                ║
 * ║                                                                            ║
 * ║  PURPOSE: Teach MCP tools and resources using the official Java MCP SDK.   ║
 * ║  This is a 1:1 port of the Python Module 01 server. It exposes structured  ║
 * ║  benefits data over MCP so an LLM client can inspect employee data,        ║
 * ║  calculate matches, estimate HSA tax savings, and read plan rules.         ║
 * ║                                                                            ║
 * ║  SAFETY: All data is fictional. This is educational only and is not        ║
 * ║  financial, tax, legal, or investment advice.                              ║
 * ║                                                                            ║
 * ║  RUN:  java -jar benefits-mcp-java-1.0.0-jar-with-deps.jar                ║
 * ║  The process speaks MCP over stdio and is normally launched by a client.   ║
 * ╚══════════════════════════════════════════════════════════════════════════════╝
 */
package com.benefits.mcp;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;
import io.modelcontextprotocol.server.McpServer;
import io.modelcontextprotocol.server.McpServerFeatures.SyncPromptSpecification;
import io.modelcontextprotocol.server.McpServerFeatures.SyncResourceSpecification;
import io.modelcontextprotocol.server.McpServerFeatures.SyncToolSpecification;
import io.modelcontextprotocol.server.McpSyncServer;
import io.modelcontextprotocol.server.transport.StdioServerTransportProvider;
import io.modelcontextprotocol.spec.McpSchema;
import io.modelcontextprotocol.spec.McpSchema.*;

import java.util.*;
import java.util.stream.Collectors;


/**
 * Standalone MCP server that mirrors the Python {@code benefits_mcp_server.py}
 * from Module 01. Communicates over stdio using the official MCP Java SDK.
 */
public class BenefitsMcpServer {

    // ═══════════════════════════════════════════════════════════════════════════
    // JSON HELPER
    // ═══════════════════════════════════════════════════════════════════════════

    private static final ObjectMapper MAPPER = new ObjectMapper()
            .enable(SerializationFeature.INDENT_OUTPUT)
            .enable(SerializationFeature.ORDER_MAP_ENTRIES_BY_KEYS);

    private static String toJson(Object data) {
        try {
            return MAPPER.writeValueAsString(data);
        } catch (JsonProcessingException e) {
            return data.toString();
        }
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // MOCK DATA
    // WHY mock data? MCP is a protocol boundary. You can learn the shape of
    // tools, resources, and client calls without connecting to payroll,
    // retirement, banking, or benefits-provider systems. Later modules replace
    // this with real tenant-scoped APIs, databases, and RAG-backed plan docs.
    // ═══════════════════════════════════════════════════════════════════════════

    static final Map<String, Object> EMPLOYEE_PROFILE = new LinkedHashMap<>(Map.ofEntries(
            Map.entry("employee_id", "EMP-1042"),
            Map.entry("name", "Jordan Lee"),
            Map.entry("age", 36),
            Map.entry("annual_salary", 120000),
            Map.entry("filing_status", "single"),
            Map.entry("estimated_federal_tax_rate", 0.24),
            Map.entry("estimated_state_tax_rate", 0.05),
            Map.entry("benefits_year", 2026)
    ));

    static final Map<String, Object> PLAN_401K = new LinkedHashMap<>(Map.ofEntries(
            Map.entry("provider", "MockRetire"),
            Map.entry("plan_name", "Acme FutureBuilder 401(k)"),
            Map.entry("employee_contribution_percent", 6.0),
            Map.entry("ytd_employee_contribution", 7200),
            Map.entry("ytd_employer_match", 5400),
            Map.entry("mock_employee_limit", 24500),
            Map.entry("catch_up_age", 50),
            Map.entry("match_formula",
                    "100% of the first 3% of pay, plus 50% of the next 3% of pay"),
            Map.entry("max_match_percent", 4.5),
            Map.entry("vesting",
                    "Employer match vests 25% per year over four years.")
    ));

    static final Map<String, Object> PLAN_HSA = new LinkedHashMap<>(Map.ofEntries(
            Map.entry("provider", "MockHealth Bank"),
            Map.entry("plan_name", "Acme HDHP + HSA"),
            Map.entry("coverage", "family"),
            Map.entry("employee_annual_election", 4200),
            Map.entry("employer_annual_contribution", 1000),
            Map.entry("ytd_employee_contribution", 2100),
            Map.entry("ytd_employer_contribution", 500),
            Map.entry("mock_family_limit", 8750),
            Map.entry("catch_up_age", 55),
            Map.entry("catch_up_amount", 1000),
            Map.entry("eligible_plan", true)
    ));

    static final Map<String, String> PLAN_DOCUMENTS = new LinkedHashMap<>(Map.of(
            "401k_plan_summary",
            "The Acme FutureBuilder 401(k) lets employees contribute a percentage of pay.\n"
                    + "The mock employer match is 100% of the first 3% of pay plus 50% of the next\n"
                    + "3% of pay, for a maximum employer match of 4.5% of eligible pay. Employer\n"
                    + "matching dollars vest 25% per year over four years.",

            "hsa_plan_summary",
            "The Acme HDHP + HSA lets eligible employees contribute to a Health Savings\n"
                    + "Account when enrolled in the qualifying high-deductible health plan. In this\n"
                    + "mock plan, Acme contributes $1,000 per year for family coverage. HSA funds roll\n"
                    + "over year to year and can be used for qualified medical expenses.",

            "benefits_faq",
            "Frequently asked mock benefits questions:\n"
                    + "- 401(k) contribution changes can be made any payroll period.\n"
                    + "- HSA election changes may require a qualifying life event unless made during\n"
                    + "  open enrollment.\n"
                    + "- This training example does not provide financial, tax, legal, or investment\n"
                    + "  advice."
    ));


    // ═══════════════════════════════════════════════════════════════════════════
    // HELPER: Build a JsonSchema for a tool's input
    // ═══════════════════════════════════════════════════════════════════════════

    /**
     * Build a property entry for a JsonSchema properties map.
     */
    private static Map<String, Object> prop(String type, String description) {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("type", type);
        m.put("description", description);
        return m;
    }

    /** Schema with no properties (no-arg tools). */
    private static JsonSchema emptySchema() {
        return new JsonSchema("object", Map.of(), List.of(), false, null, null);
    }


    // ═══════════════════════════════════════════════════════════════════════════
    // TOOL HANDLERS
    // ═══════════════════════════════════════════════════════════════════════════

    /** Tool: get_employee_profile */
    private static CallToolResult handleGetEmployeeProfile(
            Object exchange, Map<String, Object> args) {
        return new CallToolResult(toJson(EMPLOYEE_PROFILE), false);
    }

    /** Tool: get_401k_summary */
    private static CallToolResult handleGet401kSummary(
            Object exchange, Map<String, Object> args) {
        return new CallToolResult(toJson(PLAN_401K), false);
    }

    /** Tool: calculate_401k_match */
    private static CallToolResult handleCalculate401kMatch(
            Object exchange, Map<String, Object> args) {

        double salary = args.containsKey("salary")
                ? ((Number) args.get("salary")).doubleValue()
                : ((Number) EMPLOYEE_PROFILE.get("annual_salary")).doubleValue();

        double contributionPercent = args.containsKey("employee_contribution_percent")
                ? ((Number) args.get("employee_contribution_percent")).doubleValue()
                : ((Number) PLAN_401K.get("employee_contribution_percent")).doubleValue();

        double firstTier = Math.min(contributionPercent, 3.0);
        double secondTier = Math.min(Math.max(contributionPercent - 3.0, 0.0), 3.0);
        double matchPercent = firstTier + (secondTier * 0.5);
        double maxMatchPercent = ((Number) PLAN_401K.get("max_match_percent")).doubleValue();
        matchPercent = Math.min(matchPercent, maxMatchPercent);
        double annualMatch = salary * (matchPercent / 100);

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("salary", salary);
        result.put("employee_contribution_percent", contributionPercent);
        result.put("employer_match_percent", Math.round(matchPercent * 100.0) / 100.0);
        result.put("estimated_annual_employer_match", Math.round(annualMatch * 100.0) / 100.0);
        result.put("full_match_reached", contributionPercent >= 6.0);
        result.put("formula", PLAN_401K.get("match_formula"));
        result.put("educational_note",
                "Mock estimate only. Confirm rules with the real plan document.");

        return new CallToolResult(toJson(result), false);
    }

    /** Tool: estimate_annual_401k_contribution */
    private static CallToolResult handleEstimateAnnual401kContribution(
            Object exchange, Map<String, Object> args) {

        double salary = args.containsKey("salary")
                ? ((Number) args.get("salary")).doubleValue()
                : ((Number) EMPLOYEE_PROFILE.get("annual_salary")).doubleValue();

        double contributionPercent = args.containsKey("employee_contribution_percent")
                ? ((Number) args.get("employee_contribution_percent")).doubleValue()
                : ((Number) PLAN_401K.get("employee_contribution_percent")).doubleValue();

        double annualContribution = salary * (contributionPercent / 100);
        int mockLimit = ((Number) PLAN_401K.get("mock_employee_limit")).intValue();
        double remainingToLimit = mockLimit - annualContribution;

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("salary", salary);
        result.put("employee_contribution_percent", contributionPercent);
        result.put("estimated_annual_employee_contribution",
                Math.round(annualContribution * 100.0) / 100.0);
        result.put("mock_employee_limit", mockLimit);
        result.put("remaining_to_mock_limit",
                Math.round(Math.max(0.0, remainingToLimit) * 100.0) / 100.0);
        result.put("would_exceed_mock_limit", annualContribution > mockLimit);
        result.put("educational_note",
                "This uses mock plan assumptions, not official tax guidance.");

        return new CallToolResult(toJson(result), false);
    }

    /** Tool: get_hsa_summary */
    private static CallToolResult handleGetHsaSummary(
            Object exchange, Map<String, Object> args) {
        return new CallToolResult(toJson(PLAN_HSA), false);
    }

    /** Tool: estimate_hsa_tax_savings */
    private static CallToolResult handleEstimateHsaTaxSavings(
            Object exchange, Map<String, Object> args) {

        double contribution = args.containsKey("annual_contribution")
                ? ((Number) args.get("annual_contribution")).doubleValue()
                : ((Number) PLAN_HSA.get("employee_annual_election")).doubleValue();

        double defaultRate =
                ((Number) EMPLOYEE_PROFILE.get("estimated_federal_tax_rate")).doubleValue()
                        + ((Number) EMPLOYEE_PROFILE.get("estimated_state_tax_rate")).doubleValue();

        double taxRate = args.containsKey("marginal_tax_rate")
                ? ((Number) args.get("marginal_tax_rate")).doubleValue()
                : defaultRate;

        double ficaRate = 0.0765; // Social Security 6.2% + Medicare 1.45%
        double incomeTaxSavings = contribution * taxRate;
        double ficaSavings = contribution * ficaRate;

        int mockFamilyLimit = ((Number) PLAN_HSA.get("mock_family_limit")).intValue();
        int employerAnnualContribution =
                ((Number) PLAN_HSA.get("employer_annual_contribution")).intValue();

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("annual_hsa_employee_contribution", contribution);
        result.put("estimated_combined_income_tax_rate",
                Math.round(taxRate * 10000.0) / 10000.0);
        result.put("estimated_income_tax_savings",
                Math.round(incomeTaxSavings * 100.0) / 100.0);
        result.put("estimated_fica_savings",
                Math.round(ficaSavings * 100.0) / 100.0);
        result.put("estimated_total_savings",
                Math.round((incomeTaxSavings + ficaSavings) * 100.0) / 100.0);
        result.put("mock_family_limit", mockFamilyLimit);
        result.put("within_mock_limit",
                contribution + employerAnnualContribution <= mockFamilyLimit);
        result.put("fica_note",
                "FICA savings apply to HSA contributions made through payroll "
                        + "(Section 125 cafeteria plan), not direct deposits.");
        result.put("educational_note",
                "Educational estimate only. Tax treatment depends on facts and law.");

        return new CallToolResult(toJson(result), false);
    }

    /** Tool: list_plan_documents */
    private static CallToolResult handleListPlanDocuments(
            Object exchange, Map<String, Object> args) {
        List<Map<String, String>> docs = PLAN_DOCUMENTS.keySet().stream()
                .sorted()
                .map(key -> Map.of(
                        "document_id", key,
                        "title", key.replace("_", " ")
                                .substring(0, 1).toUpperCase()
                                + key.replace("_", " ").substring(1)))
                .collect(Collectors.toList());
        return new CallToolResult(toJson(docs), false);
    }

    /** Tool: get_plan_document */
    private static CallToolResult handleGetPlanDocument(
            Object exchange, Map<String, Object> args) {
        String documentId = (String) args.get("document_id");
        String text = PLAN_DOCUMENTS.get(documentId);
        if (text == null) {
            Map<String, Object> error = new LinkedHashMap<>();
            error.put("error", "Unknown document_id '" + documentId + "'.");
            error.put("available_document_ids", new ArrayList<>(PLAN_DOCUMENTS.keySet())
                    .stream().sorted().collect(Collectors.toList()));
            return new CallToolResult(toJson(error), true);
        }

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("document_id", documentId);
        result.put("title", documentId.replace("_", " ")
                .substring(0, 1).toUpperCase()
                + documentId.replace("_", " ").substring(1));
        result.put("text", text);
        return new CallToolResult(toJson(result), false);
    }

    /** Tool: search_plan_rules */
    private static CallToolResult handleSearchPlanRules(
            Object exchange, Map<String, Object> args) {
        String query = (String) args.get("query");
        int maxResults = args.containsKey("max_results")
                ? ((Number) args.get("max_results")).intValue()
                : 3;

        Set<String> words = Arrays.stream(query.split("\\s+"))
                .filter(w -> w.length() > 2)
                .map(w -> w.toLowerCase().replaceAll("[.,()\"]", ""))
                .collect(Collectors.toSet());

        List<Map.Entry<Integer, Map.Entry<String, String>>> scored = new ArrayList<>();
        for (Map.Entry<String, String> entry : PLAN_DOCUMENTS.entrySet()) {
            String normalized = entry.getValue().toLowerCase();
            int score = (int) words.stream().filter(normalized::contains).count();
            if (score > 0) {
                scored.add(Map.entry(score, entry));
            }
        }
        scored.sort((a, b) -> Integer.compare(b.getKey(), a.getKey()));

        int limit = Math.max(1, maxResults);
        List<Map<String, Object>> results = scored.stream()
                .limit(limit)
                .map(e -> {
                    Map<String, Object> m = new LinkedHashMap<>();
                    m.put("document_id", e.getValue().getKey());
                    m.put("match_score", e.getKey());
                    m.put("snippet", e.getValue().getValue());
                    return m;
                })
                .collect(Collectors.toList());

        return new CallToolResult(toJson(results), false);
    }


    // ═══════════════════════════════════════════════════════════════════════════
    // TOOL DEFINITIONS
    // Build the Tool schema objects and pair them with handlers.
    // ═══════════════════════════════════════════════════════════════════════════

    private static List<SyncToolSpecification> buildTools() {
        List<SyncToolSpecification> tools = new ArrayList<>();

        // get_employee_profile — no parameters
        tools.add(new SyncToolSpecification(
                new Tool("get_employee_profile",
                        "Return the mock employee profile used by the benefits assistant. "
                                + "Use this when a question needs employee salary, age, filing "
                                + "status, or estimated tax-rate assumptions before calculating "
                                + "401(k) or HSA outcomes.",
                        emptySchema()),
                BenefitsMcpServer::handleGetEmployeeProfile));

        // get_401k_summary — no parameters
        tools.add(new SyncToolSpecification(
                new Tool("get_401k_summary",
                        "Return the mock employee's current 401(k) plan and contribution summary.",
                        emptySchema()),
                BenefitsMcpServer::handleGet401kSummary));

        // calculate_401k_match — optional salary & employee_contribution_percent
        Map<String, Object> matchProps = new LinkedHashMap<>();
        matchProps.put("salary", prop("number",
                "Annual salary. Defaults to the mock employee salary."));
        matchProps.put("employee_contribution_percent", prop("number",
                "Employee contribution percent of pay. Defaults to the mock employee's "
                        + "current contribution rate."));
        tools.add(new SyncToolSpecification(
                new Tool("calculate_401k_match",
                        "Estimate the annual employer 401(k) match for the mock plan.",
                        new JsonSchema("object", matchProps, List.of(), false, null, null)),
                BenefitsMcpServer::handleCalculate401kMatch));

        // estimate_annual_401k_contribution — optional salary & employee_contribution_percent
        Map<String, Object> contribProps = new LinkedHashMap<>();
        contribProps.put("salary", prop("number",
                "Annual salary. Defaults to the mock employee salary."));
        contribProps.put("employee_contribution_percent", prop("number",
                "Contribution percent. Defaults to the mock employee's current "
                        + "contribution rate."));
        tools.add(new SyncToolSpecification(
                new Tool("estimate_annual_401k_contribution",
                        "Estimate annual employee 401(k) contributions and remaining mock limit.",
                        new JsonSchema("object", contribProps, List.of(), false, null, null)),
                BenefitsMcpServer::handleEstimateAnnual401kContribution));

        // get_hsa_summary — no parameters
        tools.add(new SyncToolSpecification(
                new Tool("get_hsa_summary",
                        "Return the mock employee's HSA coverage, election, balance, "
                                + "and plan summary.",
                        emptySchema()),
                BenefitsMcpServer::handleGetHsaSummary));

        // estimate_hsa_tax_savings — optional annual_contribution & marginal_tax_rate
        Map<String, Object> hsaProps = new LinkedHashMap<>();
        hsaProps.put("annual_contribution", prop("number",
                "Employee HSA contribution amount. Defaults to the mock employee "
                        + "annual election."));
        hsaProps.put("marginal_tax_rate", prop("number",
                "Combined estimated tax rate. Defaults to the mock federal plus "
                        + "state rates from the employee profile."));
        tools.add(new SyncToolSpecification(
                new Tool("estimate_hsa_tax_savings",
                        "Estimate tax savings from a mock HSA contribution.",
                        new JsonSchema("object", hsaProps, List.of(), false, null, null)),
                BenefitsMcpServer::handleEstimateHsaTaxSavings));

        // list_plan_documents — no parameters
        tools.add(new SyncToolSpecification(
                new Tool("list_plan_documents",
                        "List the mock plan documents available as MCP resources or "
                                + "keyword search.",
                        emptySchema()),
                BenefitsMcpServer::handleListPlanDocuments));

        // get_plan_document — required document_id
        Map<String, Object> docProps = new LinkedHashMap<>();
        docProps.put("document_id", prop("string",
                "e.g. \"401k_plan_summary\", \"hsa_plan_summary\", \"benefits_faq\"."));
        tools.add(new SyncToolSpecification(
                new Tool("get_plan_document",
                        "Return the full text of a mock plan document by id. "
                                + "Use list_plan_documents first to see valid ids.",
                        new JsonSchema("object", docProps, List.of("document_id"),
                                false, null, null)),
                BenefitsMcpServer::handleGetPlanDocument));

        // search_plan_rules — required query, optional max_results
        Map<String, Object> searchProps = new LinkedHashMap<>();
        searchProps.put("query", prop("string",
                "Search phrase such as \"vesting\", \"match\", \"HSA rollover\"."));
        searchProps.put("max_results", prop("integer",
                "Maximum number of matching snippets to return. Default 3."));
        tools.add(new SyncToolSpecification(
                new Tool("search_plan_rules",
                        "Keyword-search the mock plan rules. This is intentionally not RAG. "
                                + "Module 02 replaces this with embeddings, retrieval, and citations.",
                        new JsonSchema("object", searchProps, List.of("query"),
                                false, null, null)),
                BenefitsMcpServer::handleSearchPlanRules));

        return tools;
    }


    // ═══════════════════════════════════════════════════════════════════════════
    // RESOURCE DEFINITIONS
    // Resources are read-only context endpoints. Tools are verbs; resources are
    // nouns. This contrast is the core beginner lesson in this module.
    // ═══════════════════════════════════════════════════════════════════════════

    private static List<SyncResourceSpecification> buildResources() {
        List<SyncResourceSpecification> resources = new ArrayList<>();

        // benefits://employee/profile
        resources.add(new SyncResourceSpecification(
                new Resource("benefits://employee/profile",
                        "Mock Employee Profile",
                        "Read-only mock employee profile.",
                        "application/json", null),
                (exchange, request) -> new ReadResourceResult(List.of(
                        new TextResourceContents(
                                request.uri(),
                                "application/json",
                                toJson(EMPLOYEE_PROFILE))))));

        // benefits://401k/plan-summary
        resources.add(new SyncResourceSpecification(
                new Resource("benefits://401k/plan-summary",
                        "Mock 401(k) Plan Summary",
                        "Read-only mock 401(k) plan summary.",
                        "application/json", null),
                (exchange, request) -> new ReadResourceResult(List.of(
                        new TextResourceContents(
                                request.uri(),
                                "application/json",
                                toJson(PLAN_401K))))));

        // benefits://hsa/plan-summary
        resources.add(new SyncResourceSpecification(
                new Resource("benefits://hsa/plan-summary",
                        "Mock HSA Plan Summary",
                        "Read-only mock HSA plan summary.",
                        "application/json", null),
                (exchange, request) -> new ReadResourceResult(List.of(
                        new TextResourceContents(
                                request.uri(),
                                "application/json",
                                toJson(PLAN_HSA))))));

        // benefits://documents/benefits-faq
        resources.add(new SyncResourceSpecification(
                new Resource("benefits://documents/benefits-faq",
                        "Mock Benefits FAQ",
                        "Read-only mock benefits FAQ.",
                        "text/plain", null),
                (exchange, request) -> new ReadResourceResult(List.of(
                        new TextResourceContents(
                                request.uri(),
                                "text/plain",
                                PLAN_DOCUMENTS.get("benefits_faq"))))));

        return resources;
    }


    // ═══════════════════════════════════════════════════════════════════════════
    // PROMPT DEFINITIONS
    // ═══════════════════════════════════════════════════════════════════════════

    private static List<SyncPromptSpecification> buildPrompts() {
        List<SyncPromptSpecification> prompts = new ArrayList<>();

        prompts.add(new SyncPromptSpecification(
                new Prompt("benefits_question_prompt",
                        "Create a safe prompt for educational benefits questions.",
                        List.of(new PromptArgument(
                                "question",
                                "The user's benefits question.",
                                true))),
                (exchange, request) -> {
                    String question = request.arguments() != null
                            ? (String) request.arguments().getOrDefault("question", "")
                            : "";
                    String text = "You are an educational benefits assistant.\n\n"
                            + "Use MCP tools and resources to answer the user's question "
                            + "from mock data.\n"
                            + "Be clear when numbers are estimates. Do not provide financial, "
                            + "tax, legal, or\ninvestment advice.\n\n"
                            + "Question: " + question;
                    return new GetPromptResult(
                            "Educational benefits question prompt",
                            List.of(new PromptMessage(
                                    Role.USER,
                                    new TextContent(text))));
                }));

        return prompts;
    }


    // ═══════════════════════════════════════════════════════════════════════════
    // MAIN — wire everything up and start
    // ═══════════════════════════════════════════════════════════════════════════

    public static void main(String[] args) {
        // Redirect all logging to stderr so stdout stays clean for MCP JSON-RPC
        System.setProperty("org.slf4j.simpleLogger.logFile", "System.err");
        System.setProperty("org.slf4j.simpleLogger.defaultLogLevel", "warn");

        StdioServerTransportProvider transport = new StdioServerTransportProvider();

        McpSyncServer server = McpServer.sync(transport)
                .serverInfo("mock-benefits-assistant", "1.0.0")
                .capabilities(new ServerCapabilities.Builder()
                        .tools(true)
                        .resources(true, false)
                        .prompts(true)
                        .build())
                .tools(buildTools())
                .resources(buildResources())
                .prompts(buildPrompts())
                .build();

        System.err.println("[BenefitsMcpServer] MCP server running on stdio. "
                + "Waiting for client connection...");

        // The StdioServerTransportProvider blocks on System.in until the client
        // disconnects or sends EOF. No explicit run loop is needed.
    }
}
