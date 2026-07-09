package com.benefits.adk.tools;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.List;

public record ContributionProjection(
        BigDecimal annualSalary,
        BigDecimal employeePrimaryContribution,
        BigDecimal employerMatch,
        BigDecimal combinedPrimaryContribution,
        BigDecimal savingsContribution,
        BigDecimal estimatedSavingsAdjustment,
        List<String> notes
) {
    public ContributionProjection rounded() {
        return new ContributionProjection(
                money(annualSalary),
                money(employeePrimaryContribution),
                money(employerMatch),
                money(combinedPrimaryContribution),
                money(savingsContribution),
                money(estimatedSavingsAdjustment),
                notes
        );
    }

    private static BigDecimal money(BigDecimal value) {
        return value.setScale(2, RoundingMode.HALF_UP);
    }
}
