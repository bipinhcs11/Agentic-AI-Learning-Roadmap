package com.benefits.mcp.springboot;

import java.util.List;
import java.util.Map;

import org.springframework.stereotype.Service;

import com.benefits.mcp.springboot.BenefitsModels.EmployeeProfile;
import com.benefits.mcp.springboot.BenefitsModels.SavingsAccountAdjustmentEstimate;
import com.benefits.mcp.springboot.BenefitsModels.MatchEstimate;
import com.benefits.mcp.springboot.BenefitsModels.PrimaryContributionPlan;
import com.benefits.mcp.springboot.BenefitsModels.SavingsAccountPlan;
import com.benefits.mcp.springboot.BenefitsModels.SourceCatalog;

@Service
public class BenefitsDataService {

    private static final EmployeeProfile EMPLOYEE_PROFILE = new EmployeeProfile(
            "EMP-1042",
            "Jordan Lee",
            36,
            120000,
            "single",
            0.24,
            0.05,
            2026);

    private static final PrimaryContributionPlan PRIMARY_CONTRIBUTION_PLAN = new PrimaryContributionPlan(
            "Acme FutureBuilder primary contribution",
            6.0,
            7200,
            5400,
            "100% of the first 3% of pay, plus 50% of the next 3% of pay",
            4.5);

    private static final SavingsAccountPlan SAVINGS_ACCOUNT_PLAN = new SavingsAccountPlan(
            "Acme qualifying plan + savings account",
            "family",
            4200,
            1000,
            true);

    private static final SourceCatalog SOURCES = new SourceCatalog(Map.of(
            "primary_contribution_reference.md", List.of(
                    "Fixture source summary",
                    "Fixture source summary"),
            "savings_account_reference.md", List.of(
                    "Fixture source summary",
                    "Fixture source summary")));

    public EmployeeProfile employeeProfile() {
        return EMPLOYEE_PROFILE;
    }

    public PrimaryContributionPlan primaryContributionPlan() {
        return PRIMARY_CONTRIBUTION_PLAN;
    }

    public SavingsAccountPlan savingsAccountPlan() {
        return SAVINGS_ACCOUNT_PLAN;
    }

    public SourceCatalog sources() {
        return SOURCES;
    }

    public MatchEstimate calculatePrimaryContributionMatch(Double salary, Double employeeContributionPercent) {
        double resolvedSalary = salary != null ? salary : EMPLOYEE_PROFILE.annualSalary();
        double pct = employeeContributionPercent != null ? employeeContributionPercent : PRIMARY_CONTRIBUTION_PLAN.employeeContributionPercent();

        double firstTier = Math.min(pct, 3.0);
        double secondTier = Math.min(Math.max(pct - 3.0, 0.0), 3.0);
        double matchPct = Math.min(firstTier + secondTier * 0.5, PRIMARY_CONTRIBUTION_PLAN.maxMatchPercent());

        return new MatchEstimate(
                resolvedSalary,
                pct,
                round2(matchPct),
                round2(resolvedSalary * matchPct / 100.0),
                pct >= 6.0,
                "Mock estimate. Not professional advice.");
    }

    public SavingsAccountAdjustmentEstimate estimateSavingsAccountAdjustment(Double annualContribution, Double adjustmentRate) {
        double contribution = annualContribution != null ? annualContribution : SAVINGS_ACCOUNT_PLAN.employeeAnnualElection();
        double defaultRate = EMPLOYEE_PROFILE.estimatedFederalAdjustmentRate() + EMPLOYEE_PROFILE.estimatedStateAdjustmentRate();
        double rate = adjustmentRate != null ? adjustmentRate : defaultRate;
        double recordSystemRate = 0.0765;

        return new SavingsAccountAdjustmentEstimate(
                contribution,
                round2(contribution * rate),
                round2(contribution * recordSystemRate),
                round2(contribution * (rate + recordSystemRate)),
                "record-system estimate applies to record-system fixture contributions, not direct deposits.",
                "Educational estimate only. Not adjustment advice.");
    }

    private static double round2(double value) {
        return Math.round(value * 100.0) / 100.0;
    }
}
