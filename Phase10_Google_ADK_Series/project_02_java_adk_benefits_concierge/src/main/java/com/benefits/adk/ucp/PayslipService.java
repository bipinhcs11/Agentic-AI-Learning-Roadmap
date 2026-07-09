package com.benefits.adk.ucp;

import com.benefits.adk.tools.ContributionProjection;
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.ArrayList;
import java.util.List;

// Turns a computed projection into a mock pay statement preview. The
// employee sees exactly what will land on their stub: employee deferrals and the
// employer contributions the plan adds on top.
public final class PayslipService {
    // Semi-monthly gives the demo two statements per month without naming a vendor.
    public static final int SEMI_MONTHLY_PERIODS = 24;
    public static final String SEMI_MONTHLY_LABEL = "Semi-monthly (24 pay periods)";

    public Payslip buildPreview(EmployeeProfile profile, BenefitsPlanOption plan, ContributionProjection projection) {
        return build(profile, plan, projection, SEMI_MONTHLY_PERIODS, SEMI_MONTHLY_LABEL);
    }

    public Payslip build(
            EmployeeProfile profile,
            BenefitsPlanOption plan,
            ContributionProjection projection,
            int periodsPerYear,
            String payFrequencyLabel
    ) {
        if (periodsPerYear <= 0) {
            throw new IllegalArgumentException("periodsPerYear must be positive");
        }

        BigDecimal savingsEmployerSeed = plan.savingsEmployerSeed(profile.familyCoverage());

        Payslip.Line grossLine = annualToLine("Gross pay", projection.annualSalary(), periodsPerYear);
        Payslip.Line employeePrimaryLine = annualToLine("primary contribution employee (employee)", projection.employeePrimaryContribution(), periodsPerYear);
        Payslip.Line savingsEmployeeLine = annualToLine("savings account (employee)", projection.savingsContribution(), periodsPerYear);
        Payslip.Line matchLine = annualToLine("primary contribution employer match", projection.employerMatch(), periodsPerYear);
        Payslip.Line savingsSeedLine = annualToLine("savings account employer contribution", savingsEmployerSeed, periodsPerYear);

        BigDecimal preTaxPerPeriod = employeePrimaryLine.perPeriod().add(savingsEmployeeLine.perPeriod());
        BigDecimal adjustedBasePerPeriod = grossLine.perPeriod().subtract(preTaxPerPeriod).setScale(2, RoundingMode.HALF_UP);

        List<String> notes = new ArrayList<>();
        notes.add("Fictional educational pay statement preview. No real record system record was created or changed.");
        notes.add("Employer contributions (" + plan.planName() + ") do not reduce your take-home pay.");
        notes.add("Detailed deductions and true net pay are intentionally omitted; this is not professional advice.");

        return new Payslip(
                payFrequencyLabel,
                periodsPerYear,
                List.of(grossLine),
                List.of(employeePrimaryLine, savingsEmployeeLine),
                List.of(matchLine, savingsSeedLine),
                grossLine.perPeriod(),
                adjustedBasePerPeriod,
                projection.estimatedSavingsAdjustment(),
                List.copyOf(notes)
        );
    }

    private static Payslip.Line annualToLine(String label, BigDecimal annualAmount, int periodsPerYear) {
        BigDecimal annual = (annualAmount == null ? BigDecimal.ZERO : annualAmount).setScale(2, RoundingMode.HALF_UP);
        BigDecimal perPeriod = annual.divide(BigDecimal.valueOf(periodsPerYear), 2, RoundingMode.HALF_UP);
        return new Payslip.Line(label, perPeriod, annual);
    }
}
