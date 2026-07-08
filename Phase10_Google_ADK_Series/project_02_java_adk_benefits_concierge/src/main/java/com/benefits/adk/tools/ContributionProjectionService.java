package com.benefits.adk.tools;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.ArrayList;
import java.util.List;

public final class ContributionProjectionService {
    public static final BigDecimal EMPLOYEE_PRIMARY_LIMIT_2026 = new BigDecimal("24500");
    public static final BigDecimal COMBINED_PRIMARY_LIMIT_2026 = new BigDecimal("72000");
    public static final BigDecimal SAVINGS_SELF_ONLY_LIMIT_2026 = new BigDecimal("4400");
    public static final BigDecimal SAVINGS_FAMILY_LIMIT_2026 = new BigDecimal("8750");

    public ContributionProjection project(
            BigDecimal annualSalary,
            BigDecimal employeePrimaryPercent,
            BigDecimal annualSavingsContribution,
            String coverageType,
            BigDecimal adjustmentRate
    ) {
        requireNonNegative(annualSalary, "annualSalary");
        requireNonNegative(employeePrimaryPercent, "employeePrimaryPercent");
        requireNonNegative(annualSavingsContribution, "annualSavingsContribution");
        requireNonNegative(adjustmentRate, "adjustmentRate");

        BigDecimal employeePrimary = annualSalary
                .multiply(employeePrimaryPercent)
                .divide(new BigDecimal("100"), 8, RoundingMode.HALF_UP);
        BigDecimal cappedEmployeeprimary = employeePrimary.min(EMPLOYEE_PRIMARY_LIMIT_2026);
        BigDecimal rawEmployerMatch = calculateAcmeMatch(annualSalary, employeePrimaryPercent);
        BigDecimal employerMatch = capEmployerMatch(cappedEmployeeprimary, rawEmployerMatch);
        BigDecimal combined = cappedEmployeeprimary.add(employerMatch);

        BigDecimal savingsLimit = savingsLimitFor(coverageType);
        BigDecimal cappedSavingsContribution = annualSavingsContribution.min(savingsLimit);
        BigDecimal estimatedSavingsAdjustment = cappedSavingsContribution
                .multiply(adjustmentRate)
                .divide(new BigDecimal("100"), 8, RoundingMode.HALF_UP);

        List<String> notes = new ArrayList<>();
        notes.add("Fictional educational estimate; not professional advice.");
        notes.add("Mock Acme match: 100% of first 3% of pay plus 50% of next 3%.");
        if (employeePrimary.compareTo(EMPLOYEE_PRIMARY_LIMIT_2026) > 0) {
            notes.add("Employee primary contribution contribution was capped at the 2026 learning limit.");
        }
        if (rawEmployerMatch.compareTo(employerMatch) > 0) {
            notes.add("Employer match was reduced so employee + employer contributions stay within the 2026 learning limit.");
        }
        if (annualSavingsContribution.compareTo(savingsLimit) > 0) {
            notes.add("Requested savings account amount was capped at the fixture limit for " + normalizeCoverage(coverageType) + " coverage.");
        }

        return new ContributionProjection(
                annualSalary,
                cappedEmployeeprimary,
                employerMatch,
                combined,
                cappedSavingsContribution,
                estimatedSavingsAdjustment,
                List.copyOf(notes)
        ).rounded();
    }

    private static BigDecimal capEmployerMatch(BigDecimal cappedEmployeeprimary, BigDecimal rawEmployerMatch) {
        BigDecimal remainingCombinedRoom = COMBINED_PRIMARY_LIMIT_2026.subtract(cappedEmployeeprimary).max(BigDecimal.ZERO);
        return rawEmployerMatch.min(remainingCombinedRoom);
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

    private static BigDecimal savingsLimitFor(String coverage) {
        return "family".equals(normalizeCoverage(coverage)) ? SAVINGS_FAMILY_LIMIT_2026 : SAVINGS_SELF_ONLY_LIMIT_2026;
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
