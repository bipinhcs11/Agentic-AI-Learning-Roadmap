package com.benefits.adk.retrieval;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import org.junit.jupiter.api.Test;

class LocalBenefitsKnowledgeRetrieverTest {
    @Test
    void finds401kSnippetForMatchQuestion() {
        LocalBenefitsKnowledgeRetriever retriever = new LocalBenefitsKnowledgeRetriever();

        var results = retriever.search("401k", "full employer match", 1);

        assertFalse(results.isEmpty());
        assertEquals("401k", results.get(0).sourceId());
        assertTrue(results.get(0).text().contains("Mock employer match"));
    }

    @Test
    void findsHsaSnippetForEligibilityQuestion() {
        LocalBenefitsKnowledgeRetriever retriever = new LocalBenefitsKnowledgeRetriever();

        var results = retriever.search("hsa", "HDHP eligibility and Medicare", 1);

        assertFalse(results.isEmpty());
        assertEquals("hsa", results.get(0).sourceId());
        assertTrue(results.get(0).text().contains("HDHP eligibility"));
    }
}
