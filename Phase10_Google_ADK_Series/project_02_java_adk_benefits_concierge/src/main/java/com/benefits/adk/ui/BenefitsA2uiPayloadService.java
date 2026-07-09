package com.benefits.adk.ui;

import com.benefits.adk.tools.ContributionProjection;
import java.util.List;
import java.util.Map;

public final class BenefitsA2uiPayloadService {
    private final TrustedA2uiCatalog catalog;

    public BenefitsA2uiPayloadService() {
        this(new TrustedA2uiCatalog());
    }

    BenefitsA2uiPayloadService(TrustedA2uiCatalog catalog) {
        this.catalog = catalog;
    }

    public A2uiPayload projectionSummary(ContributionProjection projection) {
        A2uiComponent table = new A2uiComponent(
                "Table",
                Map.of(
                        "columns", List.of("Metric", "Amount"),
                        "rows", List.of(
                                List.of("Employee primary contribution", projection.employeePrimaryContribution().toPlainString()),
                                List.of("Employer match", projection.employerMatch().toPlainString()),
                                List.of("Combined primary contribution", projection.combinedPrimaryContribution().toPlainString()),
                                List.of("savings account contribution", projection.savingsContribution().toPlainString()),
                                List.of("Estimated savings adjustment", projection.estimatedSavingsAdjustment().toPlainString())
                        )
                ),
                List.of()
        );
        A2uiComponent note = new A2uiComponent(
                "Text",
                Map.of("text", "Fictional educational estimate. No real election has been created or submitted."),
                List.of()
        );
        A2uiComponent card = new A2uiComponent(
                "Card",
                Map.of("title", "Fictional benefits projection"),
                List.of(table, note)
        );
        A2uiValidationResult validation = catalog.validate(card);
        return new A2uiPayload("a2ui.phase10.rung01b.v1", card, validation);
    }
}
