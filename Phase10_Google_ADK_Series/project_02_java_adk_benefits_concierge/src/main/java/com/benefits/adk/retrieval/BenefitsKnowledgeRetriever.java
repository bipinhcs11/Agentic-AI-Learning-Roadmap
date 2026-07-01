package com.benefits.adk.retrieval;

import java.util.List;

public interface BenefitsKnowledgeRetriever {
    List<KnowledgeSnippet> search(String topic, String question, int maxResults);
}
