package com.benefits.adk.tools;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.ArrayList;
import java.util.List;

public final class ContributionProjectionService {
    public static final BigDecimal EMPLOYEE_401K_LIMIT_2026 = new BigDecimal("24500");
    public static final BigDecimal COMBINED_401K_LIMIT_2026 = new BigDecimal("72000");
    public static final BigDecimal HSA_SELF_ONLY_LIMIT_2026 = new BigDecimal("4400");
    public static final BigDecimal HSA_FAMILY_LIMIT_2026 = new BigDecimal("8750");

    public ContributionProjection project(
            BigDecimal annualSalary,
            BigDecimal employee401kPercent,
            BigDecimal annualHsaContribution,
            String hsaCoverage,
            BigDecimal marginalTaxRate
    ) {
        requireNonNegative(annualSalary, "annualSalary");
        requireNonNegative(employee401kPercent, "employee401kPercent");
        requireNonNegative(annualHsaContribution, "annualHsaContribution");
        requireNonNegative(marginalTaxRate, "marginalTaxRate");

        BigDecimal employee401k = annualSalary
                .multiply(employee401kPercent)
                .divide(new BigDecimal("100"), 8, RoundingMode.HALF_UP);
        BigDecimal cappedEmployee401k = employee401k.min(EMPLOYEE_401K_LIMIT_2026);
        BigDecimal employerMatch = calculateAcmeMatch(annualSalary, employee401kPercent);
        BigDecimal combined = cappedEmployee401k.add(employerMatch).min(COMBINED_401K_LIMIT_2026);
        BigDecimal estimatedHsaTaxSavings = annualHsaContribution
                .multiply(marginalTaxRate)
                .divide(new BigDecimal("100"), 8, RoundingMode.HALF_UP);

        List<String> notes = new ArrayList<>();
        notes.add("Fictional educational estimate; not legal, tax, investment, or fiduciary advice.");
        notes.add("Mock Acme match: 100% of first 3% of pay plus 50% of next 3%.");
        if (employee401k.compareTo(EMPLOYEE_401K_LIMIT_2026) > 0) {
            notes.add("Employee 401(k) contribution was capped at the 2026 learning limit.");
        }
        BigDecimal hsaLimit = hsaLimitFor(hsaCoverage);
        if (annualHsaContribution.compareTo(hsaLimit) > 0) {
            notes.add("Requested HSA amount is above the fixture limit for " + normalizeCoverage(hsaCoverage) + " coverage.");
        }

        return new ContributionProjection(
                annualSalary,
                cappedEmployee401k,
                employerMatch,
                combined,
                annualHsaContribution,
                estimatedHsaTaxSavings,
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

    private static BigDecimal hsaLimitFor(String coverage) {
        return "family".equals(normalizeCoverage(coverage)) ? HSA_FAMILY_LIMIT_2026 : HSA_SELF_ONLY_LIMIT_2026;
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
