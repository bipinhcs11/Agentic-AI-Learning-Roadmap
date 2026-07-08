package com.benefits.adk.ucp;

import java.math.BigDecimal;

// The UCP "cart": what the new hire wants to elect, before any approval or
// checkout. Nothing here is committed to a real system.
public record ProposedElection(
        String electionType,
        BigDecimal employeePrimaryPercent,
        BigDecimal annualSavingsContribution,
        String coverageType
) {
    public ProposedElection {
        electionType = electionType == null || electionType.isBlank() ? "new-hire-enrollment" : electionType.trim();
        employeePrimaryPercent = employeePrimaryPercent == null ? BigDecimal.ZERO : employeePrimaryPercent;
        annualSavingsContribution = annualSavingsContribution == null ? BigDecimal.ZERO : annualSavingsContribution;
        coverageType = coverageType == null || coverageType.isBlank() ? "self-only" : coverageType.trim();
    }
}
