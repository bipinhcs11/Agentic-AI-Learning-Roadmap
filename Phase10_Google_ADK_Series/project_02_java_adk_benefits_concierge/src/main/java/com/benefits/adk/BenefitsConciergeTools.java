package com.benefits.adk;

import com.benefits.adk.guardrails.BenefitsGuardrails;
import com.benefits.adk.guardrails.GuardrailDecision;
import com.benefits.adk.retrieval.BenefitsKnowledgeRetriever;
import com.benefits.adk.retrieval.KnowledgeSnippet;
import com.benefits.adk.retrieval.LocalBenefitsKnowledgeRetriever;
import com.benefits.adk.tools.ContributionProjection;
import com.benefits.adk.tools.ContributionProjectionService;
import com.benefits.adk.tools.ElectionDraft;
import com.benefits.adk.tools.ElectionDraftService;
import com.benefits.adk.ui.A2uiPayload;
import com.benefits.adk.ui.A2uiComponent;
import com.benefits.adk.ui.BenefitsA2uiPayloadService;
import java.math.BigDecimal;
import java.util.List;
import java.util.Map;

public final class BenefitsConciergeTools {
    private static final BenefitsGuardrails GUARDRAILS = new BenefitsGuardrails();
    private static final BenefitsKnowledgeRetriever RETRIEVER = new LocalBenefitsKnowledgeRetriever();
    private static final ContributionProjectionService PROJECTION_SERVICE = new ContributionProjectionService();
    private static final ElectionDraftService DRAFT_SERVICE = new ElectionDraftService();
    private static final BenefitsA2uiPayloadService A2UI_SERVICE = new BenefitsA2uiPayloadService();

    private BenefitsConciergeTools() {
    }

    public static GuardrailDecision screenRequest(String userRequest) {
        return GUARDRAILS.screenUserRequest(userRequest);
    }

    public static List<KnowledgeSnippet> searchBenefitsKnowledge(String topic, String question) {
        return RETRIEVER.search(topic, question, 2);
    }

    public static ContributionProjection projectContributions(
            double annualSalary,
            double employeePrimaryPercent,
            double annualSavingsContribution,
            String coverageType,
            double adjustmentRate
    ) {
        return PROJECTION_SERVICE.project(
                BigDecimal.valueOf(annualSalary),
                BigDecimal.valueOf(employeePrimaryPercent),
                BigDecimal.valueOf(annualSavingsContribution),
                coverageType,
                BigDecimal.valueOf(adjustmentRate)
        );
    }

    public static ElectionDraft draftElectionChange(
            String electionType,
            double proposedPrimaryPercent,
            double proposedAnnualSavingsContribution
    ) {
        return DRAFT_SERVICE.draft(
                electionType,
                BigDecimal.valueOf(proposedPrimaryPercent),
                BigDecimal.valueOf(proposedAnnualSavingsContribution)
        );
    }

    public static Map<String, Object> buildProjectionA2uiCard(
            double annualSalary,
            double employeePrimaryPercent,
            double annualSavingsContribution,
            String coverageType,
            double adjustmentRate
    ) {
        ContributionProjection projection = projectContributions(
                annualSalary,
                employeePrimaryPercent,
                annualSavingsContribution,
                coverageType,
                adjustmentRate
        );
        A2uiPayload payload = A2UI_SERVICE.projectionSummary(projection);
        return Map.of(
                "data", Map.of(
                        "schemaVersion", payload.schemaVersion(),
                        "root", componentToMap(payload.root()),
                        "validation", Map.of(
                                "valid", payload.validation().valid(),
                                "errors", payload.validation().errors()
                        )
                ),
                "metadata", Map.of(
                        "mimeType", "application/json+a2ui",
                        "rung", "01B",
                        "trustedCatalog", List.of("Card", "Table", "Text")
                )
        );
    }

    private static Map<String, Object> componentToMap(A2uiComponent component) {
        return Map.of(
                "type", component.type(),
                "props", component.props(),
                "children", component.children().stream()
                        .map(BenefitsConciergeTools::componentToMap)
                        .toList()
        );
    }
}
