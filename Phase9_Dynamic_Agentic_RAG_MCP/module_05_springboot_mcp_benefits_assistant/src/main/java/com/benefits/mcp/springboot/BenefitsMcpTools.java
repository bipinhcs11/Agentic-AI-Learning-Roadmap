package com.benefits.mcp.springboot;

import java.util.List;

import org.springaicommunity.mcp.annotation.McpTool;
import org.springaicommunity.mcp.annotation.McpToolParam;
import org.springframework.stereotype.Component;

import com.benefits.mcp.springboot.BenefitsModels.DocumentExcerpt;
import com.benefits.mcp.springboot.BenefitsModels.DocumentSummary;
import com.benefits.mcp.springboot.BenefitsModels.EmployeeProfile;
import com.benefits.mcp.springboot.BenefitsModels.SavingsAccountAdjustmentEstimate;
import com.benefits.mcp.springboot.BenefitsModels.MatchEstimate;
import com.benefits.mcp.springboot.BenefitsModels.PrimaryContributionPlan;
import com.benefits.mcp.springboot.BenefitsModels.SavingsAccountPlan;
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
            name = "get_primary_contribution_summary",
            description = "Return the fictional employee's current primary contribution plan and contribution summary.",
            generateOutputSchema = true)
    public PrimaryContributionPlan getPrimaryContributionSummary() {
        return benefitsData.primaryContributionPlan();
    }

    @McpTool(
            name = "calculate_primary_contribution_match",
            description = "Estimate the fictional employer primary contribution match for a salary and contribution percent.",
            generateOutputSchema = true)
    public MatchEstimate calculatePrimaryContributionMatch(
            @McpToolParam(description = "Annual salary. Defaults to the fictional employee salary.", required = false)
            Double salary,
            @McpToolParam(description = "Employee contribution percent of pay. Defaults to the fictional current rate.", required = false)
            Double employeeContributionPercent) {
        return benefitsData.calculatePrimaryContributionMatch(salary, employeeContributionPercent);
    }

    @McpTool(
            name = "get_savings_account_summary",
            description = "Return the fictional employee's savings account coverage, election, and employer contribution.",
            generateOutputSchema = true)
    public SavingsAccountPlan getSavingsAccountSummary() {
        return benefitsData.savingsAccountPlan();
    }

    @McpTool(
            name = "estimate_savings_account_adjustment",
            description = "Estimate fictional savings account adjustment savings using mock adjustment assumptions.",
            generateOutputSchema = true)
    public SavingsAccountAdjustmentEstimate estimateSavingsAccountAdjustment(
            @McpToolParam(description = "Annual employee savings account contribution. Defaults to the fictional election.", required = false)
            Double annualContribution,
            @McpToolParam(description = "Combined marginal adjustment rate. Defaults to fictional federal plus state.", required = false)
            Double adjustmentRate) {
        return benefitsData.estimateSavingsAccountAdjustment(annualContribution, adjustmentRate);
    }

    @McpTool(
            name = "search_benefits_docs",
            description = "Search the local primary contribution/savings account reference summaries. Use for rules, limits, eligibility, and citations.",
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
            description = "Return source labels used by the local reference summaries.",
            generateOutputSchema = true)
    public SourceCatalog listSources() {
        return benefitsData.sources();
    }
}
