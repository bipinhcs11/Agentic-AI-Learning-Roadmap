package com.benefits.mcp.springboot;

import java.util.List;

import org.springaicommunity.mcp.annotation.McpTool;
import org.springaicommunity.mcp.annotation.McpToolParam;
import org.springframework.stereotype.Component;

import com.benefits.mcp.springboot.BenefitsModels.DocumentExcerpt;
import com.benefits.mcp.springboot.BenefitsModels.DocumentSummary;
import com.benefits.mcp.springboot.BenefitsModels.EmployeeProfile;
import com.benefits.mcp.springboot.BenefitsModels.HsaTaxSavingsEstimate;
import com.benefits.mcp.springboot.BenefitsModels.MatchEstimate;
import com.benefits.mcp.springboot.BenefitsModels.Plan401k;
import com.benefits.mcp.springboot.BenefitsModels.PlanHsa;
import com.benefits.mcp.springboot.BenefitsModels.SearchHit;
import com.benefits.mcp.springboot.BenefitsModels.SourceCatalog;

@Component
public class BenefitsMcpTools {

    private final BenefitsDataService benefitsData;
    private final RagDocumentService ragDocuments;

    public BenefitsMcpTools(BenefitsDataService benefitsData, RagDocumentService ragDocuments) {
        this.benefitsData = benefitsData;
        this.ragDocuments = ragDocuments;
    }

    @McpTool(
            name = "get_employee_profile",
            description = "Return the fictional employee profile used by the Spring Boot benefits assistant.",
            generateOutputSchema = true)
    public EmployeeProfile getEmployeeProfile() {
        return benefitsData.employeeProfile();
    }

    @McpTool(
            name = "get_401k_summary",
            description = "Return the fictional employee's current 401(k) plan and contribution summary.",
            generateOutputSchema = true)
    public Plan401k get401kSummary() {
        return benefitsData.plan401k();
    }

    @McpTool(
            name = "calculate_401k_match",
            description = "Estimate the fictional employer 401(k) match for a salary and contribution percent.",
            generateOutputSchema = true)
    public MatchEstimate calculate401kMatch(
            @McpToolParam(description = "Annual salary. Defaults to the fictional employee salary.", required = false)
            Double salary,
            @McpToolParam(description = "Employee contribution percent of pay. Defaults to the fictional current rate.", required = false)
            Double employeeContributionPercent) {
        return benefitsData.calculate401kMatch(salary, employeeContributionPercent);
    }

    @McpTool(
            name = "get_hsa_summary",
            description = "Return the fictional employee's HSA coverage, election, and employer contribution.",
            generateOutputSchema = true)
    public PlanHsa getHsaSummary() {
        return benefitsData.planHsa();
    }

    @McpTool(
            name = "estimate_hsa_tax_savings",
            description = "Estimate fictional HSA tax savings using mock tax assumptions.",
            generateOutputSchema = true)
    public HsaTaxSavingsEstimate estimateHsaTaxSavings(
            @McpToolParam(description = "Annual employee HSA contribution. Defaults to the fictional election.", required = false)
            Double annualContribution,
            @McpToolParam(description = "Combined marginal tax rate. Defaults to fictional federal plus state.", required = false)
            Double marginalTaxRate) {
        return benefitsData.estimateHsaTaxSavings(annualContribution, marginalTaxRate);
    }

    @McpTool(
            name = "search_benefits_docs",
            description = "Search the local 401(k)/HSA reference summaries. Use for rules, limits, eligibility, and citations.",
            generateOutputSchema = true)
    public List<SearchHit> searchBenefitsDocs(
            @McpToolParam(description = "Benefits rules or limit question.", required = true)
            String query,
            @McpToolParam(description = "Number of search hits. Defaults to 4.", required = false)
            Integer k) {
        return ragDocuments.search(query, k);
    }

    @McpTool(
            name = "list_documents",
            description = "List the reference documents available to this Spring Boot RAG service.",
            generateOutputSchema = true)
    public List<DocumentSummary> listDocuments() {
        return ragDocuments.listDocuments();
    }

    @McpTool(
            name = "get_document_excerpt",
            description = "Return a bounded excerpt from a known reference document.",
            generateOutputSchema = true)
    public DocumentExcerpt getDocumentExcerpt(
            @McpToolParam(description = "Document id returned by list_documents.", required = true)
            String documentId,
            @McpToolParam(description = "Maximum characters. Defaults to 600.", required = false)
            Integer maxChars) {
        return ragDocuments.getDocumentExcerpt(documentId, maxChars);
    }

    @McpTool(
            name = "list_sources",
            description = "Return source URLs used by the local reference summaries.",
            generateOutputSchema = true)
    public SourceCatalog listSources() {
        return benefitsData.sources();
    }
}
