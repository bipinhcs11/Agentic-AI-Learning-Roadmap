package com.benefits.adk.tools;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.math.BigDecimal;
import org.junit.jupiter.api.Test;

class ContributionProjectionServiceTest {
    private final ContributionProjectionService service = new ContributionProjectionService();

    @Test
    void calculatesFullMockMatchAtSixPercent() {
        ContributionProjection projection = service.project(
                new BigDecimal("100000"),
                new BigDecimal("6"),
                new BigDecimal("4400"),
                "self-only",
                new BigDecimal("24")
        );

        assertEquals(new BigDecimal("6000.00"), projection.employeePrimaryContribution());
        assertEquals(new BigDecimal("4500.00"), projection.employerMatch());
        assertEquals(new BigDecimal("10500.00"), projection.combinedPrimaryContribution());
        assertEquals(new BigDecimal("1056.00"), projection.estimatedSavingsAdjustment());
    }

    @Test
    void capsEmployeeDeferralAtFixtureLimit() {
        ContributionProjection projection = service.project(
                new BigDecimal("500000"),
                new BigDecimal("20"),
                BigDecimal.ZERO,
                "family",
                new BigDecimal("20")
        );

        assertEquals(new BigDecimal("24500.00"), projection.employeePrimaryContribution());
        assertTrue(projection.notes().stream().anyMatch(note -> note.contains("capped")));
    }

    @Test
    void capsEmployerMatchToCombinedFixtureLimit() {
        ContributionProjection projection = service.project(
                new BigDecimal("2000000"),
                new BigDecimal("6"),
                BigDecimal.ZERO,
                "family",
                new BigDecimal("20")
        );

        assertEquals(new BigDecimal("24500.00"), projection.employeePrimaryContribution());
        assertEquals(new BigDecimal("47500.00"), projection.employerMatch());
        assertEquals(new BigDecimal("72000.00"), projection.combinedPrimaryContribution());
        assertTrue(projection.notes().stream().anyMatch(note -> note.contains("Employer match was reduced")));
    }

    @Test
    void capsSavingsContributionAtFixtureLimitBeforeEstimatingAdjustment() {
        ContributionProjection projection = service.project(
                new BigDecimal("100000"),
                new BigDecimal("6"),
                new BigDecimal("9000"),
                "family",
                new BigDecimal("20")
        );

        assertEquals(new BigDecimal("8750.00"), projection.savingsContribution());
        assertEquals(new BigDecimal("1750.00"), projection.estimatedSavingsAdjustment());
        assertTrue(projection.notes().stream().anyMatch(note -> note.contains("savings account amount was capped")));
    }
}
