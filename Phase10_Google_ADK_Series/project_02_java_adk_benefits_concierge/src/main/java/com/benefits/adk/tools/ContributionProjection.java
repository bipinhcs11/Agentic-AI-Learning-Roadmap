package com.benefits.adk.tools;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.List;

public record ContributionProjection(
        BigDecimal annualSalary,
        BigDecimal employee401kContribution,
        BigDecimal employerMatch,
        BigDecimal combined401kContribution,
        BigDecimal hsaContribution,
        BigDecimal estimatedHsaTaxSavings,
        List<String> notes
) {
    public ContributionProjection rounded() {
        return new ContributionProjection(
                money(annualSalary),
                money(employee401kContribution),
                money(employerMatch),
                money(combined401kContribution),
                money(hsaContribution),
                money(estimatedHsaTaxSavings),
                notes
        );
    }

    private static BigDecimal money(BigDecimal value) {
        return value.setScale(2, RoundingMode.HALF_UP);
    }
}
