package com.compliance.riskscoring.handler;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpHandler;

import java.io.IOException;
import java.io.OutputStream;
import java.nio.charset.StandardCharsets;
import java.util.*;

/**
 * Serves the A2A Agent Card at GET /.well-known/agent.json
 *
 * The Agent Card is the discovery mechanism for A2A agents.
 * Other agents use this to understand the capabilities and input/output formats.
 */
public class AgentCardHandler implements HttpHandler {

    private final ObjectMapper mapper;
    private final String agentUrl;
    private final byte[] cachedResponse;

    public AgentCardHandler(ObjectMapper mapper, String agentUrl) {
        this.mapper = mapper;
        this.agentUrl = agentUrl;

        // Pre-build the agent card (it's static)
        try {
            this.cachedResponse = mapper.writerWithDefaultPrettyPrinter()
                    .writeValueAsBytes(buildAgentCard());
        } catch (Exception e) {
            throw new RuntimeException("Failed to serialize agent card", e);
        }
    }

    @Override
    public void handle(HttpExchange exchange) throws IOException {
        // CORS headers
        exchange.getResponseHeaders().set("Access-Control-Allow-Origin", "*");
        exchange.getResponseHeaders().set("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
        exchange.getResponseHeaders().set("Access-Control-Allow-Headers", "Content-Type, Authorization");

        if ("OPTIONS".equalsIgnoreCase(exchange.getRequestMethod())) {
            exchange.sendResponseHeaders(204, -1);
            return;
        }

        if (!"GET".equalsIgnoreCase(exchange.getRequestMethod())) {
            exchange.sendResponseHeaders(405, -1);
            return;
        }

        exchange.getResponseHeaders().set("Content-Type", "application/json; charset=utf-8");
        exchange.sendResponseHeaders(200, cachedResponse.length);
        try (OutputStream os = exchange.getResponseBody()) {
            os.write(cachedResponse);
        }
    }

    /**
     * Builds the A2A Agent Card structure matching the protocol spec.
     */
    private Map<String, Object> buildAgentCard() {
        Map<String, Object> card = new LinkedHashMap<>();
        card.put("name", "Financial Risk Scoring Engine");
        card.put("description",
                "Java-based quantitative risk scoring engine that computes financial risk scores " +
                "for vendor contracts based on contract value, liability exposure, term duration, " +
                "insurance coverage, and structural safeguards.");
        card.put("url", agentUrl);
        card.put("version", "1.0.0");

        // Provider
        Map<String, String> provider = new LinkedHashMap<>();
        provider.put("organization", "Compliance Pipeline");
        provider.put("url", agentUrl);
        card.put("provider", provider);

        // Capabilities
        Map<String, Object> capabilities = new LinkedHashMap<>();
        capabilities.put("streaming", false);
        capabilities.put("pushNotifications", false);
        capabilities.put("stateTransitionHistory", false);
        card.put("capabilities", capabilities);

        // Skills
        Map<String, Object> skill = new LinkedHashMap<>();
        skill.put("id", "contract_risk_scoring");
        skill.put("name", "Contract Risk Scoring");
        skill.put("description",
                "Computes a quantitative financial risk score (0-100) for vendor contracts " +
                "based on contract value, liability exposure, term duration, insurance coverage, " +
                "and structural safeguards. Returns risk grade (A-F), component breakdown, and " +
                "actionable recommendations for risk mitigation.");
        skill.put("tags", List.of("risk", "scoring", "financial", "compliance", "contract"));

        // Input/Output schemas
        Map<String, Object> inputSchema = new LinkedHashMap<>();
        inputSchema.put("type", "object");
        Map<String, Object> inputProps = new LinkedHashMap<>();
        inputProps.put("contract_value", Map.of("type", "number", "description", "Total contract value in USD"));
        inputProps.put("contractor_name", Map.of("type", "string", "description", "Name of the contractor/vendor"));
        inputProps.put("client_name", Map.of("type", "string", "description", "Name of the client"));
        inputProps.put("start_date", Map.of("type", "string", "description", "Contract start date (YYYY-MM-DD)"));
        inputProps.put("end_date", Map.of("type", "string", "description", "Contract end date (YYYY-MM-DD)"));
        inputProps.put("liability_limit", Map.of("type", "string", "description", "Liability limit amount or 'unlimited'"));
        inputProps.put("insurance_coverage", Map.of("type", "number", "description", "Insurance coverage amount in USD"));
        inputProps.put("auto_renewal", Map.of("type", "boolean", "description", "Whether contract auto-renews"));
        inputProps.put("has_termination_clause", Map.of("type", "boolean", "description", "Whether contract has a termination clause"));
        inputProps.put("term_length_years", Map.of("type", "number", "description", "Contract duration in years"));
        inputSchema.put("properties", inputProps);
        inputSchema.put("required", List.of("contract_value"));

        Map<String, Object> outputSchema = new LinkedHashMap<>();
        outputSchema.put("type", "object");
        Map<String, Object> outputProps = new LinkedHashMap<>();
        outputProps.put("risk_score", Map.of("type", "integer", "description", "Overall risk score 0-100"));
        outputProps.put("risk_grade", Map.of("type", "string", "description", "Letter grade A-F"));
        outputProps.put("risk_breakdown", Map.of("type", "object", "description", "Component scores"));
        outputProps.put("recommendations", Map.of("type", "array", "description", "Risk mitigation recommendations"));
        outputProps.put("scoring_timestamp", Map.of("type", "string", "description", "ISO 8601 timestamp"));
        outputSchema.put("properties", outputProps);

        skill.put("inputSchema", inputSchema);
        skill.put("outputSchema", outputSchema);

        card.put("skills", List.of(skill));

        // Default modes
        card.put("defaultInputModes", List.of("application/json"));
        card.put("defaultOutputModes", List.of("application/json"));

        return card;
    }
}
