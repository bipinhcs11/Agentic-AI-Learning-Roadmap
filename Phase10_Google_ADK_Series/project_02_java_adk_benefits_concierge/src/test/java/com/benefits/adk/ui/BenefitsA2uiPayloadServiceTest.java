package com.benefits.adk.ui;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.benefits.adk.BenefitsConciergeTools;
import com.benefits.adk.tools.ContributionProjectionService;
import java.math.BigDecimal;
import java.util.Map;
import org.junit.jupiter.api.Test;

class BenefitsA2uiPayloadServiceTest {
    @Test
    void buildsValidatedProjectionCard() {
        var projection = new ContributionProjectionService().project(
                new BigDecimal("100000"),
                new BigDecimal("6"),
                new BigDecimal("4400"),
                "self-only",
                new BigDecimal("24")
        );

        A2uiPayload payload = new BenefitsA2uiPayloadService().projectionSummary(projection);

        assertEquals("a2ui.phase10.rung01b.v1", payload.schemaVersion());
        assertEquals("Card", payload.root().type());
        assertTrue(payload.validation().valid());
    }

    @Test
    void exposedToolReturnsA2uiDataPartShape() {
        Map<String, Object> payload = BenefitsConciergeTools.buildProjectionA2uiCard(
                100000,
                6,
                4400,
                "self-only",
                24
        );

        @SuppressWarnings("unchecked")
        Map<String, Object> metadata = (Map<String, Object>) payload.get("metadata");
        @SuppressWarnings("unchecked")
        Map<String, Object> data = (Map<String, Object>) payload.get("data");
        @SuppressWarnings("unchecked")
        Map<String, Object> root = (Map<String, Object>) data.get("root");

        assertEquals("application/json+a2ui", metadata.get("mimeType"));
        assertEquals("a2ui.phase10.rung01b.v1", data.get("schemaVersion"));
        assertEquals("Card", root.get("type"));
    }
}
