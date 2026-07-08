package com.benefits.adk.ui;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;

class TrustedA2uiCatalogTest {
    private final TrustedA2uiCatalog catalog = new TrustedA2uiCatalog();

    @Test
    void acceptsTrustedCardTableTextPayload() {
        A2uiComponent component = new A2uiComponent(
                "Card",
                Map.of("title", "Projection"),
                List.of(new A2uiComponent("Text", Map.of("text", "Fictional estimate"), List.of()))
        );

        assertTrue(catalog.validate(component).valid());
    }

    @Test
    void rejectsUntrustedComponentType() {
        A2uiComponent component = new A2uiComponent("Iframe", Map.of("src", "https://example.com"), List.of());

        A2uiValidationResult result = catalog.validate(component);

        assertFalse(result.valid());
        assertTrue(result.errors().stream().anyMatch(error -> error.contains("untrusted component")));
    }

    @Test
    void rejectsExecutableProps() {
        A2uiComponent component = new A2uiComponent("Text", Map.of("onClick", "submitrecord system()"), List.of());

        A2uiValidationResult result = catalog.validate(component);

        assertFalse(result.valid());
        assertTrue(result.errors().stream().anyMatch(error -> error.contains("blocked prop")));
    }
}
