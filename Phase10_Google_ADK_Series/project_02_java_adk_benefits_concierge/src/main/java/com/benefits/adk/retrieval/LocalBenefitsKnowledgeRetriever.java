package com.benefits.adk.retrieval;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.stream.Collectors;

public final class LocalBenefitsKnowledgeRetriever implements BenefitsKnowledgeRetriever {
    private static final Map<String, String> RESOURCES = Map.of(
            "primary", "/benefits-kb/primary_contribution_reference.md",
            "savings", "/benefits-kb/savings_contribution_reference.md"
    );

    private final List<KnowledgeSnippet> snippets;

    public LocalBenefitsKnowledgeRetriever() {
        this.snippets = RESOURCES.entrySet().stream()
                .map(entry -> loadSnippet(entry.getKey(), entry.getValue()))
                .toList();
    }

    @Override
    public List<KnowledgeSnippet> search(String topic, String question, int maxResults) {
        String query = ((topic == null ? "" : topic) + " " + (question == null ? "" : question))
                .toLowerCase(Locale.ROOT);
        int limit = Math.max(1, maxResults);

        return snippets.stream()
                .sorted(Comparator.comparingInt((KnowledgeSnippet snippet) -> score(snippet, query)).reversed())
                .limit(limit)
                .toList();
    }

    private static KnowledgeSnippet loadSnippet(String sourceId, String resourcePath) {
        try (InputStream stream = LocalBenefitsKnowledgeRetriever.class.getResourceAsStream(resourcePath)) {
            if (stream == null) {
                throw new IllegalStateException("Missing benefits knowledge resource: " + resourcePath);
            }
            String text = new BufferedReader(new InputStreamReader(stream, StandardCharsets.UTF_8))
                    .lines()
                    .collect(Collectors.joining("\n"));
            String title = text.lines()
                    .filter(line -> line.startsWith("# "))
                    .findFirst()
                    .map(line -> line.substring(2))
                    .orElse(sourceId);
            return new KnowledgeSnippet(sourceId, title, text);
        } catch (IOException exception) {
            throw new IllegalStateException("Unable to load benefits knowledge resource: " + resourcePath, exception);
        }
    }

    private static int score(KnowledgeSnippet snippet, String query) {
        List<String> terms = tokenize(query);
        String haystack = (snippet.sourceId() + " " + snippet.title() + " " + snippet.text())
                .toLowerCase(Locale.ROOT);
        int score = 0;
        for (String term : terms) {
            if (haystack.contains(term)) {
                score++;
            }
        }
        return score;
    }

    private static List<String> tokenize(String query) {
        if (query.isBlank()) {
            return List.of();
        }
        String[] rawTerms = query.split("[^a-z0-9]+");
        List<String> terms = new ArrayList<>();
        for (String term : rawTerms) {
            if (term.length() > 2) {
                terms.add(term);
            }
        }
        return terms;
    }
}
