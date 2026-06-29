package com.compliance.riskscoring.scoring;

import com.compliance.riskscoring.model.ContractDetails;
import com.compliance.riskscoring.model.RiskScore;

import java.time.Instant;
import java.time.format.DateTimeFormatter;
import java.util.*;

/**
 * Pure deterministic risk scoring engine.
 *
 * Computes a quantitative financial risk score (0-100) based on five components:
 *   1. Contract Value Risk   (0-30): Higher contract value = higher risk
 *   2. Liability Risk        (0-25): Unlimited liability = maximum risk
 *   3. Term Duration Risk    (0-15): Longer terms = more risk
 *   4. Insurance Gap Risk    (0-15): Under-insured contracts are riskier
 *   5. Structural Risk       (0-15): Missing safeguards increase risk
 *
 * No AI/LLM dependencies — this is a rules-based calculator.
 */
public class RiskCalculator {

    // --- Contract Value Risk Thresholds (max 30 points) ---
    private static final double VALUE_TIER_1 = 50_000.0;    // 0-50K → 5 pts
    private static final double VALUE_TIER_2 = 100_000.0;   // 50K-100K → 10 pts
    private static final double VALUE_TIER_3 = 250_000.0;   // 100K-250K → 15 pts
    private static final double VALUE_TIER_4 = 500_000.0;   // 250K-500K → 20 pts
    private static final double VALUE_TIER_5 = 1_000_000.0; // 500K-1M → 25 pts
    // > 1M → 30 pts

    // --- Liability Risk (max 25 points) ---
    private static final int LIABILITY_UNLIMITED = 25;
    private static final int LIABILITY_CAPPED = 0;

    // --- Term Duration Risk Thresholds (max 15 points) ---
    private static final double TERM_SHORT = 1.0;   // ≤1 year → 3 pts
    private static final double TERM_MED = 2.0;     // 1-2 years → 6 pts
    private static final double TERM_LONG = 3.0;    // 2-3 years → 9 pts
    private static final double TERM_VLONG = 5.0;   // 3-5 years → 12 pts
    // > 5 years → 15 pts

    // --- Insurance Gap Risk (max 15 points) ---
    private static final double COVERAGE_RATIO_EXCELLENT = 2.0;  // ≥2x → 0 pts
    private static final double COVERAGE_RATIO_GOOD = 1.5;       // 1.5-2x → 3 pts
    private static final double COVERAGE_RATIO_ADEQUATE = 1.0;   // 1-1.5x → 6 pts
    private static final double COVERAGE_RATIO_LOW = 0.5;        // 0.5-1x → 10 pts
    // < 0.5x → 15 pts

    /**
     * Computes the full risk score for the given contract details.
     *
     * @param contract the extracted contract fields
     * @return a RiskScore with the total score, grade, breakdown, and recommendations
     */
    public RiskScore calculate(ContractDetails contract) {
        int valueRisk = computeContractValueRisk(contract.getContractValue());
        int liabilityRisk = computeLiabilityRisk(contract);
        int termRisk = computeTermDurationRisk(contract.getTermLengthYears());
        int insuranceRisk = computeInsuranceGapRisk(
                contract.getContractValue(), contract.getInsuranceCoverage());
        int structuralRisk = computeStructuralRisk(
                contract.isHasTerminationClause(), contract.isAutoRenewal());

        int totalScore = Math.min(100,
                valueRisk + liabilityRisk + termRisk + insuranceRisk + structuralRisk);

        String grade = computeGrade(totalScore);

        // Build the breakdown
        Map<String, Object> breakdown = new LinkedHashMap<>();
        breakdown.put("contract_value_risk", valueRisk);
        breakdown.put("contract_value_risk_max", 30);
        breakdown.put("liability_risk", liabilityRisk);
        breakdown.put("liability_risk_max", 25);
        breakdown.put("term_duration_risk", termRisk);
        breakdown.put("term_duration_risk_max", 15);
        breakdown.put("insurance_gap_risk", insuranceRisk);
        breakdown.put("insurance_gap_risk_max", 15);
        breakdown.put("structural_risk", structuralRisk);
        breakdown.put("structural_risk_max", 15);

        // Generate recommendations
        List<String> recommendations = generateRecommendations(
                contract, valueRisk, liabilityRisk, termRisk, insuranceRisk, structuralRisk);

        // Assemble the result
        RiskScore result = new RiskScore();
        result.setRiskScore(totalScore);
        result.setRiskGrade(grade);
        result.setRiskBreakdown(breakdown);
        result.setRecommendations(recommendations);
        result.setScoringTimestamp(
                DateTimeFormatter.ISO_INSTANT.format(Instant.now()));
        result.setContractorName(contract.getContractorName());
        result.setClientName(contract.getClientName());
        result.setContractValue(contract.getContractValue());

        return result;
    }

    /**
     * Contract Value Risk: 0 → 30 points.
     * Higher contract values carry more financial exposure.
     */
    public int computeContractValueRisk(double value) {
        if (value <= 0) return 0;
        if (value <= VALUE_TIER_1) return 5;
        if (value <= VALUE_TIER_2) return 10;
        if (value <= VALUE_TIER_3) return 15;
        if (value <= VALUE_TIER_4) return 20;
        if (value <= VALUE_TIER_5) return 25;
        return 30; // > $1M
    }

    /**
     * Liability Risk: 0 or 25 points.
     * Unlimited liability is the single biggest risk factor.
     */
    public int computeLiabilityRisk(ContractDetails contract) {
        return contract.isLiabilityUnlimited() ? LIABILITY_UNLIMITED : LIABILITY_CAPPED;
    }

    /**
     * Term Duration Risk: 0 → 15 points.
     * Longer contract terms lock in risk for extended periods.
     */
    public int computeTermDurationRisk(double termYears) {
        if (termYears <= 0) return 0;
        if (termYears <= TERM_SHORT) return 3;
        if (termYears <= TERM_MED) return 6;
        if (termYears <= TERM_LONG) return 9;
        if (termYears <= TERM_VLONG) return 12;
        return 15; // > 5 years
    }

    /**
     * Insurance Gap Risk: 0 → 15 points.
     * Inadequate insurance coverage relative to contract value is risky.
     */
    public int computeInsuranceGapRisk(double contractValue, double insuranceCoverage) {
        if (contractValue <= 0) return 0;
        if (insuranceCoverage <= 0) return 15; // No insurance at all

        double ratio = insuranceCoverage / contractValue;

        if (ratio >= COVERAGE_RATIO_EXCELLENT) return 0;
        if (ratio >= COVERAGE_RATIO_GOOD) return 3;
        if (ratio >= COVERAGE_RATIO_ADEQUATE) return 6;
        if (ratio >= COVERAGE_RATIO_LOW) return 10;
        return 15; // < 0.5x coverage
    }

    /**
     * Structural Risk: 0 → 15 points.
     * Missing termination clause or presence of auto-renewal are structural weaknesses.
     */
    public int computeStructuralRisk(boolean hasTerminationClause, boolean autoRenewal) {
        int risk = 0;
        if (!hasTerminationClause) {
            risk += 10; // No exit strategy
        }
        if (autoRenewal) {
            risk += 5; // Automatic lock-in risk
        }
        return Math.min(risk, 15);
    }

    /**
     * Assigns a letter grade based on the total score.
     *   A: 0-20  (Low risk)
     *   B: 21-40 (Moderate risk)
     *   C: 41-60 (Elevated risk)
     *   D: 61-80 (High risk)
     *   F: 81-100 (Critical risk)
     */
    public String computeGrade(int totalScore) {
        if (totalScore <= 20) return "A";
        if (totalScore <= 40) return "B";
        if (totalScore <= 60) return "C";
        if (totalScore <= 80) return "D";
        return "F";
    }

    /**
     * Generates actionable risk mitigation recommendations based on component scores.
     */
    private List<String> generateRecommendations(
            ContractDetails contract,
            int valueRisk,
            int liabilityRisk,
            int termRisk,
            int insuranceRisk,
            int structuralRisk) {

        List<String> recs = new ArrayList<>();

        // Contract value recommendations
        if (valueRisk >= 25) {
            recs.add("HIGH VALUE CONTRACT (>$500K): Require executive-level approval and enhanced due diligence before signing.");
        } else if (valueRisk >= 15) {
            recs.add("Consider phased payment milestones to reduce upfront financial exposure on this mid-to-high value contract.");
        }

        // Liability recommendations
        if (liabilityRisk > 0) {
            recs.add("CRITICAL: Negotiate a liability cap. Unlimited liability exposes the organization to unbounded financial risk.");
            recs.add("Recommend capping liability at 1-2x the total contract value as an industry standard safeguard.");
        }

        // Term duration recommendations
        if (termRisk >= 12) {
            recs.add("Long-term contract (>3 years): Include periodic review clauses and performance benchmarks at annual intervals.");
        } else if (termRisk >= 9) {
            recs.add("Medium-term contract: Ensure price adjustment clauses are included to hedge against market changes.");
        }

        // Insurance gap recommendations
        if (insuranceRisk >= 10) {
            recs.add(String.format(
                    "INSURANCE GAP: Coverage ($%,.0f) is significantly below the contract value ($%,.0f). " +
                    "Require the vendor to increase coverage to at least 1.5x the contract value.",
                    contract.getInsuranceCoverage(), contract.getContractValue()));
        } else if (insuranceRisk >= 6) {
            recs.add("Insurance coverage meets minimum requirements but consider requesting increased coverage for better protection.");
        }

        // Structural recommendations
        if (!contract.isHasTerminationClause()) {
            recs.add("ADD TERMINATION CLAUSE: Without a termination for convenience clause, the organization cannot exit the contract without cause.");
        }
        if (contract.isAutoRenewal()) {
            recs.add("AUTO-RENEWAL PRESENT: Set calendar reminders for the opt-out window. Consider negotiating removal of auto-renewal or adding a notice period.");
        }

        // If everything looks good
        if (recs.isEmpty()) {
            recs.add("Contract risk profile is within acceptable parameters. Standard monitoring procedures apply.");
        }

        return recs;
    }
}
