package com.benefits.adk.ucp;

import java.math.BigDecimal;

// A fictional new-hire record. There is no real HRIS behind this; all fields
// are supplied by the caller / demo and are treated as educational examples.
public record EmployeeProfile(
        String employeeId,
        String fullName,
        EmployeeCategory category,
        BigDecimal annualSalary,
        String coverageType,
        BigDecimal adjustmentRatePercent
) {
    public EmployeeProfile {
        employeeId = employeeId == null || employeeId.isBlank() ? "EMP-DEMO" : employeeId.trim();
        fullName = fullName == null || fullName.isBlank() ? "New Hire (fictional)" : fullName.trim();
        category = category == null ? EmployeeCategory.STANDARD : category;
        annualSalary = annualSalary == null ? BigDecimal.ZERO : annualSalary;
        coverageType = coverageType == null || coverageType.isBlank() ? "self-only" : coverageType.trim();
        adjustmentRatePercent = adjustmentRatePercent == null ? BigDecimal.ZERO : adjustmentRatePercent;
    }

    public boolean familyCoverage() {
        return "family".equals(coverageType.toLowerCase().replace('_', '-'));
    }
}
