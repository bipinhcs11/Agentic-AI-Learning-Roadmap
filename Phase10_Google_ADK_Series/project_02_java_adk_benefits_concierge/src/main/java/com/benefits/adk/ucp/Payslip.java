package com.benefits.adk.ucp;

import java.math.BigDecimal;
import java.util.List;

// A fictional, mock pay statement preview. It only carries the
// benefits-relevant lines (earnings, employee deductions, employer
// contributions) plus a adjusted base. It deliberately does NOT compute taxes
// or true net pay, to avoid implying personalized professional advice.
public record Payslip(
        String payFrequency,
        int periodsPerYear,
        List<Line> earnings,
        List<Line> employeeDeductions,
        List<Line> employerContributions,
        BigDecimal grossPerPeriod,
        BigDecimal adjustedBasePerPeriod,
        BigDecimal estimatedAnnualSavingsAdjustment,
        List<String> notes
) {
    // One statement line with both the per-pay-period and annual amount, the
    // shape a simple statement row shows.
    public record Line(String label, BigDecimal perPeriod, BigDecimal annual) {
    }

    public Payslip {
        earnings = earnings == null ? List.of() : List.copyOf(earnings);
        employeeDeductions = employeeDeductions == null ? List.of() : List.copyOf(employeeDeductions);
        employerContributions = employerContributions == null ? List.of() : List.copyOf(employerContributions);
        notes = notes == null ? List.of() : List.copyOf(notes);
    }
}
