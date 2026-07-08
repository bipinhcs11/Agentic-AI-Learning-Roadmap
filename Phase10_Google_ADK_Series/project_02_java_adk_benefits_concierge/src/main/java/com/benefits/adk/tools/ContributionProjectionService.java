package com.benefits.adk.tools;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.ArrayList;
import java.util.List;

public final class ContributionProjectionService {
    public static final BigDecimal EMPLOYEE_PRIMARY_CONTRIBUTION_LIMIT_2026 = new BigDecimal("24500");
    public static final BigDecimal COMBINED_PRIMARY_CONTRIBUTION_LIMIT_2026 = new BigDecimal("72000");
    public static final BigDecimal SAVINGS_ACCOUNT_SELF_ONLY_LIMIT_2026 = new BigDecimal("4400");
    public static final BigDecimal SAVINGS_ACCOUNT_FAMILY_LIMIT_2026 = new BigDecimal("8750");

    public ContributionProjection project(
            BigDecimal annualSalary,
            BigDecimal primaryContributionPercent,
            BigDecimal annualSavingsAccountContribution,
            String savingsAccountCoverage,
            BigDecimal adjustmentRate
    ) {
        requireNonNegative(annualSalary, "annualSalary");
        requireNonNegative(primaryContributionPercent, "primaryContributionPercent");
        requireNonNegative(annualSavingsAccountContribution, "annualSavingsAccountContribution");
        requireNonNegative(adjustmentRate, "adjustmentRate");

        BigDecimal employeePrimaryContribution = annualSalary
                .multiply(primaryContributionPercent)
                .divide(new BigDecimal("100"), 8, RoundingMode.HALF_UP);
        BigDecimal cappedEmployeePrimaryContribution = employeePrimaryContribution.min(EMPLOYEE_PRIMARY_CONTRIBUTION_LIMIT_2026);
        BigDecimal employerMatch = calculateAcmeMatch(annualSalary, primaryContributionPercent);
        BigDecimal combined = cappedEmployeePrimaryContribution.add(employerMatch).min(COMBINED_PRIMARY_CONTRIBUTION_LIMIT_2026);
        BigDecimal estimatedSavingsAccountAdjustment = annualSavingsAccountContribution
                .multiply(adjustmentRate)
                .divide(new BigDecimal("100"), 8, RoundingMode.HALF_UP);

        List<String> notes = new ArrayList<>();
        notes.add("Fictional educational estimate; not legal, adjustment, allocation, or individualized advice.");
        notes.add("Mock Acme match: 100% of first 3% of pay plus 50% of next 3%.");
        if (employeePrimaryContribution.compareTo(EMPLOYEE_PRIMARY_CONTRIBUTION_LIMIT_2026) > 0) {
            notes.add("Employee primary contribution was capped at the 2026 learning limit.");
        }
        BigDecimal savingsAccountLimit = savingsAccountLimitFor(savingsAccountCoverage);
        if (annualSavingsAccountContribution.compareTo(savingsAccountLimit) > 0) {
            notes.add("Requested savings account amount is above the fixture limit for " + normalizeCoverage(savingsAccountCoverage) + " coverage.");
        }

        return new ContributionProjection(
                annualSalary,
                cappedEmployeePrimaryContribution,
                employerMatch,
                combined,
                annualSavingsAccountContribution,
                estimatedSavingsAccountAdjustment,
                List.copyOf(notes)
        ).rounded();
    }

    private static BigDecimal calculateAcmeMatch(BigDecimal salary, BigDecimal employeePercent) {
        BigDecimal firstThreePercent = salary.multiply(new BigDecimal("0.03"));
        BigDecimal nextThreeEligiblePercent = employeePercent
                .subtract(new BigDecimal("3"))
                .max(BigDecimal.ZERO)
                .min(new BigDecimal("3"));
        BigDecimal nextThreeMatch = salary
                .multiply(nextThreeEligiblePercent)
                .divide(new BigDecimal("100"), 8, RoundingMode.HALF_UP)
                .multiply(new BigDecimal("0.5"));
        if (employeePercent.compareTo(new BigDecimal("3")) < 0) {
            return salary.multiply(employeePercent).divide(new BigDecimal("100"), 8, RoundingMode.HALF_UP);
        }
        return firstThreePercent.add(nextThreeMatch);
    }

    private static BigDecimal savingsAccountLimitFor(String coverage) {
        return "family".equals(normalizeCoverage(coverage)) ? SAVINGS_ACCOUNT_FAMILY_LIMIT_2026 : SAVINGS_ACCOUNT_SELF_ONLY_LIMIT_2026;
    }

    private static String normalizeCoverage(String coverage) {
        return coverage == null ? "self-only" : coverage.trim().toLowerCase().replace("_", "-");
    }

    private static void requireNonNegative(BigDecimal value, String fieldName) {
        if (value == null || value.compareTo(BigDecimal.ZERO) < 0) {
            throw new IllegalArgumentException(fieldName + " must be non-negative");
        }
    }
}
