package com.example.engineering;

import java.io.IOException;
import java.util.ArrayList;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.core.io.ClassPathResource;
import org.springframework.stereotype.Component;

/** Deliberately narrow compatibility exercise, not a complete OpenAPI diff engine. */
@Component
class ContractReview {
    private final ObjectMapper mapper;
    ContractReview(ObjectMapper mapper) { this.mapper = mapper; }

    String reviewFixtures() {
        try (var before = new ClassPathResource("fixtures/inventory-v1.json").getInputStream();
             var after = new ClassPathResource("fixtures/inventory-v2.json").getInputStream()) {
            return compare(mapper.readTree(before), mapper.readTree(after));
        } catch (IOException ex) {
            throw new IllegalStateException("Contract fixture unavailable", ex);
        }
    }

    String compare(JsonNode before, JsonNode after) {
        String pointer = "/paths/~1items/get/responses/200/content/application~1json/schema/items";
        JsonNode oldItem = before.at(pointer);
        JsonNode newItem = after.at(pointer);
        if (!oldItem.isObject() || !newItem.isObject())
            throw new IllegalArgumentException("Expected inline GET /items response schemas");
        var findings = new ArrayList<String>();
        for (JsonNode required : oldItem.path("required")) {
            String field = required.asText();
            if (!newItem.path("properties").has(field)) findings.add("removed required response field: " + field);
            else if (!oldItem.path("properties").path(field).path("type")
                .equals(newItem.path("properties").path(field).path("type")))
                findings.add("changed response type: " + field);
            else {
                boolean stillRequired = false;
                for (JsonNode candidate : newItem.path("required")) if (candidate.asText().equals(field)) stillRequired = true;
                if (!stillRequired) findings.add("required response field became optional: " + field);
            }
        }
        return findings.isEmpty() ? "No breaking change in the checked required response fields; other compatibility rules are not checked."
            : "Breaking fixture changes: " + String.join("; ", findings) + ". Block promotion pending contract review.";
    }
}
