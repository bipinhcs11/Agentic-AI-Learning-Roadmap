package com.benefits.adk.tools;

import java.math.BigDecimal;
import java.util.List;

public final class ElectionDraftService {
    public ElectionDraft draft(String electionType, BigDecimal proposed401kPercent, BigDecimal proposedAnnualHsaContribution) {
        return new ElectionDraft(
                electionType == null || electionType.isBlank() ? "educational-example" : electionType,
                proposed401kPercent == null ? BigDecimal.ZERO : proposed401kPercent,
                proposedAnnualHsaContribution == null ? BigDecimal.ZERO : proposedAnnualHsaContribution,
                false,
                List.of(
                        "Review the fictional projection.",
                        "Confirm this is only a draft in Rung 01A.",
                        "Wait for Module 02 UCP before any executable transaction lane exists."
                )
        );
    }
}
