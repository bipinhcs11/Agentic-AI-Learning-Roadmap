package com.benefits.mcp.springboot;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Set;
import java.util.regex.Pattern;

import org.springframework.core.io.Resource;
import org.springframework.core.io.support.PathMatchingResourcePatternResolver;
import org.springframework.stereotype.Service;

import com.benefits.mcp.springboot.BenefitsModels.DocumentExcerpt;
import com.benefits.mcp.springboot.BenefitsModels.DocumentSummary;
import com.benefits.mcp.springboot.BenefitsModels.SearchHit;

@Service
public class RagDocumentService {

    private static final Pattern WORD_SPLIT = Pattern.compile("[^a-z0-9$+]+");

    private final List<DocumentChunk> chunks;

    public RagDocumentService() {
        this.chunks = loadChunks();
    }

    public List<SearchHit> search(String query, Integer k) {
        int limit = k == null || k < 1 ? 4 : k;
        return chunks.stream()
                .map(chunk -> new SearchHit(chunk.source(), chunk.heading(), chunk.text(), score(query, chunk)))
                .sorted(Comparator.comparingDouble(SearchHit::score).reversed())
                .limit(limit)
                .toList();
    }

    public List<DocumentSummary> listDocuments() {
        return chunks.stream()
                .map(chunk -> chunk.source())
                .distinct()
                .sorted()
                .map(source -> new DocumentSummary(source, source, "ready"))
                .toList();
    }

    public DocumentExcerpt getDocumentExcerpt(String documentId, Integer maxChars) {
        String safeDocumentId = documentId == null ? "" : documentId.replace("/", "").replace("\\", "");
        String body = chunks.stream()
                .filter(chunk -> chunk.source().equals(safeDocumentId))
                .map(DocumentChunk::text)
                .reduce("", (a, b) -> a.isBlank() ? b : a + "\n\n" + b);
        if (body.isBlank()) {
            throw new IllegalArgumentException("Unknown document: " + documentId);
        }
        int limit = maxChars == null || maxChars < 1 ? 600 : maxChars;
        return new DocumentExcerpt(safeDocumentId, body.substring(0, Math.min(limit, body.length())));
    }

    private double score(String query, DocumentChunk chunk) {
        String queryLower = query.toLowerCase(Locale.ROOT);
        String textLower = chunk.text().toLowerCase(Locale.ROOT);
        Set<String> words = keywords(queryLower);
        double score = words.stream().filter(textLower::contains).count();

        String topic = topic(chunk.source() + " " + chunk.heading());
        if (!topic.isBlank() && queryTopics(queryLower).contains(topic)) {
            score += 3.0;
        }

        String intent = contributionIntent(queryLower);
        if (!intent.isBlank()) {
            String kind = contributionKind(chunk.heading());
            if (intent.equals(kind)) {
                score += 5.0;
            } else if (!kind.isBlank()) {
                score -= 5.0;
            }
        }
        return score;
    }

    private static Set<String> keywords(String text) {
        Set<String> out = new LinkedHashSet<>();
        for (String word : WORD_SPLIT.split(text.toLowerCase(Locale.ROOT))) {
            if (word.length() > 2) {
                out.add(word);
            }
        }
        return out;
    }

    private static Set<String> queryTopics(String queryLower) {
        Set<String> topics = new LinkedHashSet<>();
        if (queryLower.contains("hsa") || queryLower.contains("health savings") || queryLower.contains("hdhp")) {
            topics.add("hsa");
        }
        if (queryLower.contains("401k") || queryLower.contains("401(k)") || queryLower.contains("match")
                || queryLower.contains("deferral") || queryLower.contains("elective")) {
            topics.add("401k");
        }
        return topics;
    }

    private static String topic(String text) {
        String lower = text.toLowerCase(Locale.ROOT);
        if (lower.contains("hsa")) {
            return "hsa";
        }
        if (lower.contains("401k") || lower.contains("401(k)")) {
            return "401k";
        }
        return "";
    }

    private static String contributionIntent(String queryLower) {
        if (queryLower.contains("combined") || queryLower.contains("total limit")
                || queryLower.contains("overall") || queryLower.contains("annual addition")
                || queryLower.contains("employee + employer") || queryLower.contains("employee and employer")) {
            return "combined";
        }
        if (queryLower.contains("employee") || queryLower.contains("elective")
                || queryLower.contains("salary deferral") || queryLower.contains("salary-deferral")
                || queryLower.contains("my contribution") || queryLower.contains("i contribute")) {
            return "employee";
        }
        return "";
    }

    private static String contributionKind(String heading) {
        String lower = heading.toLowerCase(Locale.ROOT);
        if (lower.contains("combined") && lower.contains("employer")) {
            return "combined";
        }
        if (lower.contains("employee contribution") || lower.contains("salary-deferral")) {
            return "employee";
        }
        return "";
    }

    private static List<DocumentChunk> loadChunks() {
        try {
            Resource[] resources = new PathMatchingResourcePatternResolver()
                    .getResources("classpath:/benefits-docs/*.md");
            List<DocumentChunk> loaded = new ArrayList<>();
            for (Resource resource : resources) {
                String source = resource.getFilename();
                String text = resource.getContentAsString(StandardCharsets.UTF_8);
                loaded.addAll(sectionChunks(source == null ? "unknown.md" : source, text));
            }
            if (loaded.isEmpty()) {
                throw new IllegalStateException("No benefits docs loaded from classpath:/benefits-docs");
            }
            return List.copyOf(loaded);
        } catch (IOException e) {
            throw new IllegalStateException("Could not load benefits docs", e);
        }
    }

    private static List<DocumentChunk> sectionChunks(String source, String text) {
        String title = source;
        List<DocumentChunk> out = new ArrayList<>();
        String currentHeading = title;
        StringBuilder body = new StringBuilder();

        for (String line : text.split("\\R")) {
            if (line.startsWith("# ")) {
                title = line.substring(2).trim();
                currentHeading = title;
                continue;
            }
            if (line.startsWith("## ")) {
                addChunk(out, source, currentHeading, body);
                currentHeading = title + " — " + line.substring(3).trim();
                body = new StringBuilder();
                continue;
            }
            body.append(line).append('\n');
        }
        addChunk(out, source, currentHeading, body);
        return out;
    }

    private static void addChunk(List<DocumentChunk> out, String source, String heading, StringBuilder body) {
        String text = body.toString().trim();
        if (!text.isBlank() && !heading.toLowerCase(Locale.ROOT).endsWith("sources")) {
            out.add(new DocumentChunk(source, heading, "[" + heading + "]\n" + text));
        }
    }

    private record DocumentChunk(String source, String heading, String text) {
    }
}
