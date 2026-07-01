package com.benefits.adk.tools;

import java.math.BigDecimal;
import java.util.List;

public record ElectionDraft(
        String electionType,
        BigDecimal proposed401kPercent,
        BigDecimal proposedAnnualHsaContribution,
        boolean executableInRung01A,
        List<String> approvalSteps
) {
}
