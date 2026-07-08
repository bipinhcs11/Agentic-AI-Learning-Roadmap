package com.benefits.adk.ucp;

import static org.junit.jupiter.api.Assertions.assertEquals;

import java.math.BigDecimal;
import org.junit.jupiter.api.Test;

class BenefitsPlanCatalogTest {
    private final BenefitsPlanCatalog catalog = new BenefitsPlanCatalog();
    private static final BigDecimal SALARY = new BigDecimal("90000");
    private static final BigDecimal SIX_PERCENT = new BigDecimal("6");

    @Test
    void standardPlanMatchesFirstThreeThenHalfOfNextThree() {
        BenefitsPlanOption plan = catalog.lookup(EmployeeCategory.STANDARD);
        assertEquals(new BigDecimal("4050.00"), plan.employerMatch(SALARY, SIX_PERCENT));
        assertEquals(new BigDecimal("1000.00"), plan.savingsEmployerSeed(true));
    }

    @Test
    void executivePlanMatchesFullSixPercentWithLargerSavingsSeed() {
        BenefitsPlanOption plan = catalog.lookup(EmployeeCategory.EXECUTIVE);
        assertEquals(new BigDecimal("5400.00"), plan.employerMatch(SALARY, SIX_PERCENT));
        assertEquals(new BigDecimal("2000.00"), plan.savingsEmployerSeed(true));
    }

    @Test
    void partTimePlanMatchesHalfOfFirstThreeAndNoSavingsSeed() {
        BenefitsPlanOption plan = catalog.lookup(EmployeeCategory.PART_TIME);
        assertEquals(new BigDecimal("1350.00"), plan.employerMatch(SALARY, SIX_PERCENT));
        assertEquals(new BigDecimal("0.00"), plan.savingsEmployerSeed(true));
    }

    @Test
    void looseCategoryLabelsResolveToAPlan() {
        assertEquals(EmployeeCategory.EXECUTIVE, EmployeeCategory.fromLabel("Exec"));
        assertEquals(EmployeeCategory.PART_TIME, EmployeeCategory.fromLabel("part-time"));
        assertEquals(EmployeeCategory.STANDARD, EmployeeCategory.fromLabel(null));
    }
}
