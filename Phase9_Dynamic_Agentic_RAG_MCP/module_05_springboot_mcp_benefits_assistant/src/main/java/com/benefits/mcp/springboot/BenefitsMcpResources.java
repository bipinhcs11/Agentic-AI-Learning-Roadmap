package com.benefits.mcp.springboot;

import java.util.List;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;

import org.springaicommunity.mcp.annotation.McpResource;
import org.springframework.stereotype.Component;

import io.modelcontextprotocol.spec.McpSchema.ReadResourceResult;
import io.modelcontextprotocol.spec.McpSchema.TextResourceContents;

@Component
public class BenefitsMcpResources {

    private final BenefitsDataService benefitsData;
    private final RagDocumentService ragDocuments;
    private final ObjectMapper objectMapper;

    public BenefitsMcpResources(BenefitsDataService benefitsData, RagDocumentService ragDocuments, ObjectMapper objectMapper) {
        this.benefitsData = benefitsData;
        this.ragDocuments = ragDocuments;
        this.objectMapper = objectMapper;
    }

    @McpResource(
            uri = "benefits://employee/profile",
            name = "Mock employee profile",
            description = "Fictional employee data used for learning MCP.",
            mimeType = "application/json")
    public ReadResourceResult employeeProfile() {
        return jsonResource("benefits://employee/profile", benefitsData.employeeProfile());
    }

    @McpResource(
            uri = "benefits://401k/plan-summary",
            name = "Mock 401(k) plan summary",
            description = "Fictional 401(k) account and match summary.",
            mimeType = "application/json")
    public ReadResourceResult plan401k() {
        return jsonResource("benefits://401k/plan-summary", benefitsData.plan401k());
    }

    @McpResource(
            uri = "benefits://hsa/plan-summary",
            name = "Mock HSA plan summary",
            description = "Fictional HSA plan and election summary.",
            mimeType = "application/json")
    public ReadResourceResult planHsa() {
        return jsonResource("benefits://hsa/plan-summary", benefitsData.planHsa());
    }

    @McpResource(
            uri = "benefits://documents/catalog",
            name = "Benefits reference document catalog",
            description = "List the local RAG documents bundled with the Spring Boot service.",
            mimeType = "application/json")
    public ReadResourceResult documentCatalog() {
        return jsonResource("benefits://documents/catalog", ragDocuments.listDocuments());
    }

    private ReadResourceResult jsonResource(String uri, Object value) {
        try {
            return new ReadResourceResult(List.of(
                    new TextResourceContents(uri, "application/json", objectMapper.writeValueAsString(value))));
        } catch (JsonProcessingException e) {
            throw new IllegalStateException("Could not serialize MCP resource " + uri, e);
        }
    }
}
