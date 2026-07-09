package com.benefits.adk.ucp;

import static org.junit.jupiter.api.Assertions.assertEquals;

import com.benefits.adk.tools.ContributionProjection;
import java.math.BigDecimal;
import java.util.List;
import org.junit.jupiter.api.Test;

class PayslipServiceTest {
    private final PayslipService payslipService = new PayslipService();
    private final BenefitsPlanCatalog catalog = new BenefitsPlanCatalog();

    @Test
    void buildsMockPayStatementPerPeriodAndAnnualLines() {
        EmployeeProfile employee = new EmployeeProfile("EMP-1042", "Jordan Rivers", EmployeeCategory.STANDARD,
                new BigDecimal("90000"), "family", new BigDecimal("22"));
        ContributionProjection projection = new ContributionProjection(
                new BigDecimal("90000"),
                new BigDecimal("5400"),
                new BigDecimal("4050"),
                new BigDecimal("9450"),
                new BigDecimal("6000"),
                new BigDecimal("1320"),
                List.of()
        );

        Payslip payslip = payslipService.buildPreview(employee, catalog.lookup(EmployeeCategory.STANDARD), projection);

        assertEquals(24, payslip.periodsPerYear());
        assertEquals(new BigDecimal("3750.00"), payslip.earnings().get(0).perPeriod());
        assertEquals(new BigDecimal("90000.00"), payslip.earnings().get(0).annual());
        assertEquals(new BigDecimal("225.00"), payslip.employeeDeductions().get(0).perPeriod());
        assertEquals(new BigDecimal("250.00"), payslip.employeeDeductions().get(1).perPeriod());
        assertEquals(new BigDecimal("168.75"), payslip.employerContributions().get(0).perPeriod());
        assertEquals(new BigDecimal("41.67"), payslip.employerContributions().get(1).perPeriod());
        assertEquals(new BigDecimal("3275.00"), payslip.adjustedBasePerPeriod());
    }
}
