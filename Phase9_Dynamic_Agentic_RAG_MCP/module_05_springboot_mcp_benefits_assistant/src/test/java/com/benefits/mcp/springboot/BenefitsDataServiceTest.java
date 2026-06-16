package com.benefits.mcp.springboot;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;

class BenefitsDataServiceTest {

    private final BenefitsDataService service = new BenefitsDataService();

    @Test
    void calculatesFullMatchAtSixPercent() {
        var estimate = service.calculate401kMatch(120000.0, 6.0);

        assertThat(estimate.employerMatchPercent()).isEqualTo(4.5);
        assertThat(estimate.estimatedAnnualEmployerMatch()).isEqualTo(5400.0);
        assertThat(estimate.fullMatchReached()).isTrue();
    }

    @Test
    void estimatesHsaTaxSavingsWithDefaultRates() {
        var estimate = service.estimateHsaTaxSavings(null, null);

        assertThat(estimate.annualHsaEmployeeContribution()).isEqualTo(4200.0);
        assertThat(estimate.estimatedTotalSavings()).isEqualTo(1539.3);
    }
}
