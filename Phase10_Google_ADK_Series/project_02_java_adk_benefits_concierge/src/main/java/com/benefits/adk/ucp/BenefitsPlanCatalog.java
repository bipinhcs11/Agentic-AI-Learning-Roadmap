package com.benefits.adk.ucp;

import com.benefits.adk.ucp.BenefitsPlanOption.MatchTier;
import java.math.BigDecimal;
import java.util.List;

// The UCP "catalog" capability for this fictional employer. Given an employee
// category it returns the plan option (match tiers + savings account employer seed).
// Numbers are educational fixtures, not a real plan document.
public final class BenefitsPlanCatalog {

    public BenefitsPlanOption lookup(EmployeeCategory category) {
        EmployeeCategory resolved = category == null ? EmployeeCategory.STANDARD : category;
        return switch (resolved) {
            case EXECUTIVE -> new BenefitsPlanOption(
                    EmployeeCategory.EXECUTIVE,
                    "Acme Executive Plan (fictional)",
                    List.of(new MatchTier(new BigDecimal("6"), new BigDecimal("1.0"))),
                    new BigDecimal("1000"),
                    new BigDecimal("2000")
            );
            case PART_TIME -> new BenefitsPlanOption(
                    EmployeeCategory.PART_TIME,
                    "Acme Part-Time Plan (fictional)",
                    List.of(new MatchTier(new BigDecimal("3"), new BigDecimal("0.5"))),
                    BigDecimal.ZERO,
                    BigDecimal.ZERO
            );
            default -> new BenefitsPlanOption(
                    EmployeeCategory.STANDARD,
                    "Acme Standard Plan (fictional)",
                    List.of(
                            new MatchTier(new BigDecimal("3"), new BigDecimal("1.0")),
                            new MatchTier(new BigDecimal("6"), new BigDecimal("0.5"))
                    ),
                    new BigDecimal("500"),
                    new BigDecimal("1000")
            );
        };
    }
}
