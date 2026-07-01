package com.benefits.adk;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;

public final class ExportA2uiFixtureApp {
    private ExportA2uiFixtureApp() {
    }

    public static void main(String[] args) throws Exception {
        ObjectMapper mapper = new ObjectMapper().enable(SerializationFeature.INDENT_OUTPUT);
        var payload = BenefitsConciergeTools.buildProjectionA2uiCard(
                100000,
                6,
                4400,
                "self-only",
                24
        );
        System.out.println(mapper.writeValueAsString(payload));
    }
}
