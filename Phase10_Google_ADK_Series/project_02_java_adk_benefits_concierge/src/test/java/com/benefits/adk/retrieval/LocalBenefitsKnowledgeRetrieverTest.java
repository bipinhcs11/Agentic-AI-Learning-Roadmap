package com.benefits.adk.retrieval;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import org.junit.jupiter.api.Test;

class LocalBenefitsKnowledgeRetrieverTest {
    @Test
    void findsPrimaryContributionSnippetForMatchQuestion() {
        LocalBenefitsKnowledgeRetriever retriever = new LocalBenefitsKnowledgeRetriever();

        var results = retriever.search("primary_contribution", "full employer match", 1);

        assertFalse(results.isEmpty());
        assertEquals("primary_contribution", results.get(0).sourceId());
        assertTrue(results.get(0).text().contains("Mock employer match"));
    }

    @Test
    void findsSavingsAccountSnippetForEligibilityQuestion() {
        LocalBenefitsKnowledgeRetriever retriever = new LocalBenefitsKnowledgeRetriever();

        var results = retriever.search("savings_account", "qualifying plan eligibility and Medicare", 1);

        assertFalse(results.isEmpty());
        assertEquals("savings_account", results.get(0).sourceId());
        assertTrue(results.get(0).text().contains("qualifying plan eligibility"));
    }
}
