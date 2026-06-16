package com.benefits.mcp.springboot;

import java.util.List;
import java.util.Map;

import org.springframework.stereotype.Service;

import com.benefits.mcp.springboot.BenefitsModels.EmployeeProfile;
import com.benefits.mcp.springboot.BenefitsModels.HsaTaxSavingsEstimate;
import com.benefits.mcp.springboot.BenefitsModels.MatchEstimate;
import com.benefits.mcp.springboot.BenefitsModels.Plan401k;
import com.benefits.mcp.springboot.BenefitsModels.PlanHsa;
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

    private static final Plan401k PLAN_401K = new Plan401k(
            "Acme FutureBuilder 401(k)",
            6.0,
            7200,
            5400,
            "100% of the first 3% of pay, plus 50% of the next 3% of pay",
            4.5);

    private static final PlanHsa PLAN_HSA = new PlanHsa(
            "Acme HDHP + HSA",
            "family",
            4200,
            1000,
            true);

    private static final SourceCatalog SOURCES = new SourceCatalog(Map.of(
            "401k_reference.md", List.of(
                    "IRS — 401(k) limit increases to $24,500 for 2026: https://www.irs.gov/newsroom/401k-limit-increases-to-24500-for-2026-ira-limit-increases-to-7500",
                    "Fidelity — 401(k) contribution limits 2025 and 2026: https://www.fidelity.com/learning-center/smart-money/401k-contribution-limits"),
            "hsa_reference.md", List.of(
                    "IRS Revenue Procedure 2025-19: https://www.irs.gov/pub/irs-drop/rp-25-19.pdf",
                    "Fidelity — HSA contribution limits and eligibility 2026: https://www.fidelity.com/learning-center/smart-money/hsa-contribution-limits")));

    public EmployeeProfile employeeProfile() {
        return EMPLOYEE_PROFILE;
    }

    public Plan401k plan401k() {
        return PLAN_401K;
    }

    public PlanHsa planHsa() {
        return PLAN_HSA;
    }

    public SourceCatalog sources() {
        return SOURCES;
    }

    public MatchEstimate calculate401kMatch(Double salary, Double employeeContributionPercent) {
        double resolvedSalary = salary != null ? salary : EMPLOYEE_PROFILE.annualSalary();
        double pct = employeeContributionPercent != null ? employeeContributionPercent : PLAN_401K.employeeContributionPercent();

        double firstTier = Math.min(pct, 3.0);
        double secondTier = Math.min(Math.max(pct - 3.0, 0.0), 3.0);
        double matchPct = Math.min(firstTier + secondTier * 0.5, PLAN_401K.maxMatchPercent());

        return new MatchEstimate(
                resolvedSalary,
                pct,
                round2(matchPct),
                round2(resolvedSalary * matchPct / 100.0),
                pct >= 6.0,
                "Mock estimate. Not financial advice.");
    }

    public HsaTaxSavingsEstimate estimateHsaTaxSavings(Double annualContribution, Double marginalTaxRate) {
        double contribution = annualContribution != null ? annualContribution : PLAN_HSA.employeeAnnualElection();
        double defaultRate = EMPLOYEE_PROFILE.estimatedFederalTaxRate() + EMPLOYEE_PROFILE.estimatedStateTaxRate();
        double rate = marginalTaxRate != null ? marginalTaxRate : defaultRate;
        double ficaRate = 0.0765;

        return new HsaTaxSavingsEstimate(
                contribution,
                round2(contribution * rate),
                round2(contribution * ficaRate),
                round2(contribution * (rate + ficaRate)),
                "FICA savings apply to payroll Section 125 contributions, not direct deposits.",
                "Educational estimate only. Not tax advice.");
    }

    private static double round2(double value) {
        return Math.round(value * 100.0) / 100.0;
    }
}
