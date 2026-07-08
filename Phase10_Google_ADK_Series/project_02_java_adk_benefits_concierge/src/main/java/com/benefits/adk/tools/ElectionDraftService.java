package com.benefits.adk.tools;

import java.math.BigDecimal;
import java.util.List;

public final class ElectionDraftService {
    public ElectionDraft draft(String electionType, BigDecimal proposedPrimaryPercent, BigDecimal proposedAnnualSavingsContribution) {
        return new ElectionDraft(
                electionType == null || electionType.isBlank() ? "educational-example" : electionType,
                proposedPrimaryPercent == null ? BigDecimal.ZERO : proposedPrimaryPercent,
                proposedAnnualSavingsContribution == null ? BigDecimal.ZERO : proposedAnnualSavingsContribution,
                false,
                List.of(
                        "Review the fictional projection.",
                        "Confirm this is only a draft in Rung 01A.",
                        "Wait for Module 02 UCP before any executable transaction lane exists."
                )
        );
    }
}
