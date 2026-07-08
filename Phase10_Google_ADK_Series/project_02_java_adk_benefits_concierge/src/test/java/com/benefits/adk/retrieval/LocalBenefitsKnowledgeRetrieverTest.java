package com.benefits.adk.retrieval;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import org.junit.jupiter.api.Test;

class LocalBenefitsKnowledgeRetrieverTest {
    @Test
    void findsPrimarySnippetForMatchQuestion() {
        LocalBenefitsKnowledgeRetriever retriever = new LocalBenefitsKnowledgeRetriever();

        var results = retriever.search("primary", "full employer match", 1);

        assertFalse(results.isEmpty());
        assertEquals("primary", results.get(0).sourceId());
        assertTrue(results.get(0).text().contains("Mock employer match"));
    }

    @Test
    void findsSavingsSnippetForEligibilityQuestion() {
        LocalBenefitsKnowledgeRetriever retriever = new LocalBenefitsKnowledgeRetriever();

        var results = retriever.search("savings", "HDHP eligibility and Medicare", 1);

        assertFalse(results.isEmpty());
        assertEquals("savings", results.get(0).sourceId());
        assertTrue(results.get(0).text().contains("HDHP eligibility"));
    }
}
