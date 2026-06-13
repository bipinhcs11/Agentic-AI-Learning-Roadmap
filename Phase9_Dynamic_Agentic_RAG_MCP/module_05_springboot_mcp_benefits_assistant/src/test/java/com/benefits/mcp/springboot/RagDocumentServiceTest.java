package com.benefits.mcp.springboot;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;

class RagDocumentServiceTest {

    private final RagDocumentService service = new RagDocumentService();

    @Test
    void ranksEmployeeContributionLimitAboveCombinedLimit() {
        var hits = service.search("What is the 2026 401(k) employee contribution limit?", 4);

        assertThat(hits.get(0).heading()).contains("Employee contribution limits");
        assertThat(hits.get(0).text()).contains("$24,500");
        assertThat(hits)
                .anySatisfy(hit -> assertThat(hit.text()).contains("$72,000"));
    }

    @Test
    void searchesHsaFamilyLimitInHsaDocument() {
        var hits = service.search("What is the 2026 HSA family contribution limit?", 1);

        assertThat(hits).hasSize(1);
        assertThat(hits.get(0).source()).isEqualTo("hsa_reference.md");
        assertThat(hits.get(0).text()).contains("$8,750");
    }
}
