package com.benefits.mcp.springboot;

import java.util.List;
import java.util.Map;

public final class BenefitsModels {

    private BenefitsModels() {
    }

    public record EmployeeProfile(
            String employeeId,
            String name,
            int age,
            double annualSalary,
            String filingStatus,
            double estimatedFederalTaxRate,
            double estimatedStateTaxRate,
            int benefitsYear) {
    }

    public record Plan401k(
            String planName,
            double employeeContributionPercent,
            double ytdEmployeeContribution,
            double ytdEmployerMatch,
            String matchFormula,
            double maxMatchPercent) {
    }

    public record PlanHsa(
            String planName,
            String coverage,
            double employeeAnnualElection,
            double employerAnnualContribution,
            boolean eligiblePlan) {
    }

    public record MatchEstimate(
            double salary,
            double employeeContributionPercent,
            double employerMatchPercent,
            double estimatedAnnualEmployerMatch,
            boolean fullMatchReached,
            String educationalNote) {
    }

    public record HsaTaxSavingsEstimate(
            double annualHsaEmployeeContribution,
            double estimatedIncomeTaxSavings,
            double estimatedFicaSavings,
            double estimatedTotalSavings,
            String ficaNote,
            String educationalNote) {
    }

    public record SearchHit(
            String source,
            String heading,
            String text,
            double score) {
    }

    public record DocumentSummary(
            String documentId,
            String filename,
            String status) {
    }

    public record DocumentExcerpt(
            String documentId,
            String excerpt) {
    }

    public record SourceCatalog(Map<String, List<String>> sources) {
    }

    public record MatchRequest(Double salary, Double employeeContributionPercent) {
    }

    public record AgentQuestionRequest(String question) {
    }

    public record AgentToolTrace(
            String name,
            String target,
            Map<String, Object> arguments,
            String status) {
    }

    public record AgentDemoResponse(
            String route,
            String routeLabel,
            String backend,
            String answer,
            List<AgentToolTrace> toolCalls,
            List<SearchHit> retrievedDocuments,
            List<String> citations) {
    }
}
