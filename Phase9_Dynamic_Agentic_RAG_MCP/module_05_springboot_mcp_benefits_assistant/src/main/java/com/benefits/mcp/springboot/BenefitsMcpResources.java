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
            uri = "benefits://primary-contribution/plan-summary",
            name = "Mock primary contribution plan summary",
            description = "Fictional primary contribution account and match summary.",
            mimeType = "application/json")
    public ReadResourceResult primaryContributionPlan() {
        return jsonResource("benefits://primary-contribution/plan-summary", benefitsData.primaryContributionPlan());
    }

    @McpResource(
            uri = "benefits://savings-account/plan-summary",
            name = "Mock savings account plan summary",
            description = "Fictional savings account plan and election summary.",
            mimeType = "application/json")
    public ReadResourceResult savingsAccountPlan() {
        return jsonResource("benefits://savings-account/plan-summary", benefitsData.savingsAccountPlan());
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
