package com.benefits.mcp.springboot;

import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import org.springframework.stereotype.Service;

import com.benefits.mcp.springboot.BenefitsModels.AgentDemoResponse;
import com.benefits.mcp.springboot.BenefitsModels.AgentToolTrace;
import com.benefits.mcp.springboot.BenefitsModels.EmployeeProfile;
import com.benefits.mcp.springboot.BenefitsModels.SavingsAccountAdjustmentEstimate;
import com.benefits.mcp.springboot.BenefitsModels.MatchEstimate;
import com.benefits.mcp.springboot.BenefitsModels.PrimaryContributionPlan;
import com.benefits.mcp.springboot.BenefitsModels.SavingsAccountPlan;
import com.benefits.mcp.springboot.BenefitsModels.SearchHit;

@Service
public class BenefitsDemoAgentService {

    private static final String DEFAULT_QUESTION = "I contribute 6% to my primary contribution. Am I getting the full match, and what is the 2026 employee limit?";
    private static final Pattern PERCENT_PATTERN = Pattern.compile("(\\d+(?:\\.\\d+)?)\\s*%");

    private final BenefitsDataService benefitsData;
    private final RagDocumentService ragDocuments;

    public BenefitsDemoAgentService(BenefitsDataService benefitsData, RagDocumentService ragDocuments) {
        this.benefitsData = benefitsData;
        this.ragDocuments = ragDocuments;
    }

    public AgentDemoResponse answer(String question) {
        String safeQuestion = question == null || question.isBlank() ? DEFAULT_QUESTION : question.trim();
        String lower = safeQuestion.toLowerCase(Locale.ROOT);
        Route route = chooseRoute(lower);
        boolean useMcp = route == Route.MCP_ONLY || route == Route.MCP_RAG;
        boolean useRag = route == Route.RAG_ONLY || route == Route.MCP_RAG;

        List<AgentToolTrace> tools = new ArrayList<>();
        EmployeeProfile profile = null;
        PrimaryContributionPlan primaryContributionPlan = null;
        MatchEstimate match = null;
        SavingsAccountPlan savingsAccountPlan = null;
        SavingsAccountAdjustmentEstimate savingsAccountAdjustmentSavings = null;

        if (useMcp) {
            profile = benefitsData.employeeProfile();
            tools.add(tool("get_employee_profile", "MCP account tool",
                    Map.of("employeeId", profile.employeeId())));

            if (isSavingsAccountQuestion(lower) && !isPrimaryContributionQuestion(lower)) {
                savingsAccountPlan = benefitsData.savingsAccountPlan();
                tools.add(tool("get_savings_account_summary", "MCP account tool",
                        Map.of("planName", savingsAccountPlan.planName())));
                savingsAccountAdjustmentSavings = benefitsData.estimateSavingsAccountAdjustment(null, null);
                tools.add(tool("estimate_savings_account_adjustment", "MCP account tool",
                        Map.of("annualContribution", savingsAccountPlan.employeeAnnualElection(),
                                "adjustmentRate", profile.estimatedFederalAdjustmentRate() + profile.estimatedStateAdjustmentRate())));
            } else {
                primaryContributionPlan = benefitsData.primaryContributionPlan();
                tools.add(tool("get_primary_contribution_summary", "MCP account tool",
                        Map.of("planName", primaryContributionPlan.planName())));
                double percent = firstPercent(lower, primaryContributionPlan.employeeContributionPercent());
                match = benefitsData.calculatePrimaryContributionMatch(profile.annualSalary(), percent);
                tools.add(tool("calculate_primary_contribution_match", "MCP account tool",
                        Map.of("salary", profile.annualSalary(),
                                "employeeContributionPercent", percent)));
            }
        }

        List<SearchHit> hits = List.of();
        if (useRag) {
            hits = ragDocuments.search(safeQuestion, 3);
            tools.add(tool("search_benefits_docs", "RAG retrieval tool",
                    Map.of("query", safeQuestion, "k", 3)));
            tools.add(tool("list_sources", "RAG citation tool", Map.of()));
        }

        List<String> citations = useRag ? citationsFor(hits) : List.of();
        String answer = buildAnswer(route, safeQuestion, profile, match, savingsAccountAdjustmentSavings, hits);

        return new AgentDemoResponse(
                route.code,
                route.label,
                "Spring Boot MCP + RAG microservice",
                answer,
                List.copyOf(tools),
                hits,
                citations);
    }

    private Route chooseRoute(String lower) {
        boolean account = mentionsAccount(lower);
        boolean rules = mentionsRules(lower);

        if (account && rules) {
            return Route.MCP_RAG;
        }
        if (account) {
            return Route.MCP_ONLY;
        }
        if (rules) {
            return Route.RAG_ONLY;
        }
        return Route.DIRECT;
    }

    private static boolean mentionsAccount(String lower) {
        return lower.contains("my ")
                || lower.contains(" i ")
                || lower.startsWith("i ")
                || lower.contains("me ")
                || lower.contains("profile")
                || lower.contains("salary")
                || lower.contains("paycheck")
                || lower.contains("full match")
                || lower.contains("adjustment savings");
    }

    private static boolean mentionsRules(String lower) {
        return lower.contains("2026")
                || lower.contains("limit")
                || lower.contains("public fixture")
                || lower.contains("fixture reference")
                || lower.contains("rule")
                || lower.contains("eligible")
                || lower.contains("eligibility")
                || lower.contains("source")
                || lower.contains("reference")
                || lower.contains("document")
                || lower.contains("maximum")
                || lower.contains("cap");
    }

    private static boolean isPrimaryContributionQuestion(String lower) {
        return lower.contains("primary_contribution") || lower.contains("primary contribution") || lower.contains("match");
    }

    private static boolean isSavingsAccountQuestion(String lower) {
        return lower.contains("savings_account") || lower.contains("savings account") || lower.contains("qualifying plan");
    }

    private static double firstPercent(String lower, double fallback) {
        Matcher matcher = PERCENT_PATTERN.matcher(lower);
        return matcher.find() ? Double.parseDouble(matcher.group(1)) : fallback;
    }

    private AgentToolTrace tool(String name, String target, Map<String, Object> arguments) {
        return new AgentToolTrace(name, target, arguments, "ok");
    }

    private List<String> citationsFor(List<SearchHit> hits) {
        Map<String, List<String>> sources = benefitsData.sources().sources();
        Set<String> citations = new LinkedHashSet<>();
        for (SearchHit hit : hits) {
            List<String> sourceUrls = sources.getOrDefault(hit.source(), List.of());
            citations.addAll(sourceUrls);
        }
        return List.copyOf(citations);
    }

    private static String buildAnswer(
            Route route,
            String question,
            EmployeeProfile profile,
            MatchEstimate match,
            SavingsAccountAdjustmentEstimate savingsAccountAdjustmentSavings,
            List<SearchHit> hits) {

        if (route == Route.DIRECT) {
            return "This demo can answer general benefits questions directly, then escalate to MCP tools, RAG retrieval, or both when the question needs account data or policy references. Educational only - not professional, adjustment, legal, or allocation advice.";
        }

        StringBuilder answer = new StringBuilder();
        if (match != null && profile != null) {
            answer.append(String.format(Locale.US,
                    "For %s, a %.1f%% primary contribution on a $%,.0f salary estimates a %.1f%% employer match, or about $%,.0f per year. %s",
                    profile.name(),
                    match.employeeContributionPercent(),
                    match.salary(),
                    match.employerMatchPercent(),
                    match.estimatedAnnualEmployerMatch(),
                    match.fullMatchReached() ? "That reaches the full mock match." : "That does not reach the full mock match yet."));
        }

        if (savingsAccountAdjustmentSavings != null) {
            if (!answer.isEmpty()) {
                answer.append(" ");
            }
            answer.append(String.format(Locale.US,
                    "The mock savings account election estimates about $%,.0f in total adjustment savings, including income-adjustment and record system-adjustment components.",
                    savingsAccountAdjustmentSavings.estimatedTotalSavings()));
        }

        if (!hits.isEmpty()) {
            if (!answer.isEmpty()) {
                answer.append(" ");
            }
            SearchHit top = hits.get(0);
            answer.append("RAG retrieved ")
                    .append(top.source())
                    .append(" under \"")
                    .append(top.heading())
                    .append("\". ")
                    .append(compact(top.text()));
        }

        if (answer.isEmpty()) {
            answer.append("I routed \"").append(question).append("\" but did not find a stronger demo path.");
        }

        answer.append(" Educational only - not professional, adjustment, legal, or allocation advice.");
        return answer.toString();
    }

    private static String compact(String text) {
        String cleaned = text.replaceAll("\\[[^\\]]+\\]\\s*", "")
                .replace("**", "")
                .replaceAll("\\s+", " ")
                .trim();
        if (cleaned.length() <= 260) {
            return cleaned;
        }
        return cleaned.substring(0, 257).trim() + "...";
    }

    private enum Route {
        DIRECT("direct", "Direct"),
        MCP_ONLY("mcp", "MCP only"),
        RAG_ONLY("rag", "RAG only"),
        MCP_RAG("mcp+rag", "MCP + RAG");

        private final String code;
        private final String label;

        Route(String code, String label) {
            this.code = code;
            this.label = label;
        }
    }
}
