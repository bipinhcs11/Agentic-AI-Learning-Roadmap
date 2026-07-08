package com.benefits.mcp.springboot;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;

class BenefitsDemoAgentServiceTest {

    private final BenefitsDemoAgentService service = new BenefitsDemoAgentService(
            new BenefitsDataService(),
            new RagDocumentService());

    @Test
    void routesCombinedPersonalAndPolicyQuestionToMcpAndRag() {
        var response = service.answer(
                "I contribute 6% to my primary contribution. Am I getting the full match, and what is the 2026 employee limit?");

        assertThat(response.route()).isEqualTo("mcp+rag");
        assertThat(response.toolCalls())
                .extracting("name")
                .contains("get_employee_profile", "calculate_primary_contribution_match", "search_benefits_docs", "list_sources");
        assertThat(response.retrievedDocuments()).isNotEmpty();
        assertThat(response.answer()).contains("$5,400", "$24,500");
    }

    @Test
    void routesPolicyQuestionToRagOnly() {
        var response = service.answer("What is the 2026 savings account family contribution limit?");

        assertThat(response.route()).isEqualTo("rag");
        assertThat(response.toolCalls())
                .extracting("name")
                .containsExactly("search_benefits_docs", "list_sources");
        assertThat(response.retrievedDocuments().get(0).source()).isEqualTo("savings_account_reference.md");
        assertThat(response.answer()).contains("$8,750");
    }

    @Test
    void routesGeneralQuestionDirectly() {
        var response = service.answer("What can this benefits assistant do?");

        assertThat(response.route()).isEqualTo("direct");
        assertThat(response.toolCalls()).isEmpty();
        assertThat(response.retrievedDocuments()).isEmpty();
        assertThat(response.answer()).contains("directly");
    }
}
