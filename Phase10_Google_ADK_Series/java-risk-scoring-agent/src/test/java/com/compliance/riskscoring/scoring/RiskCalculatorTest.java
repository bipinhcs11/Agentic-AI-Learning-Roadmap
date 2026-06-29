package com.compliance.riskscoring.scoring;

import com.compliance.riskscoring.model.ContractDetails;
import com.compliance.riskscoring.model.RiskScore;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Unit tests for the deterministic risk scoring logic.
 * Tests all five component scores and the overall grading.
 */
class RiskCalculatorTest {

    private RiskCalculator calculator;

    @BeforeEach
    void setUp() {
        calculator = new RiskCalculator();
    }

    // ==================== Contract Value Risk Tests ====================

    @Test
    @DisplayName("Contract value $0 → 0 risk points")
    void testContractValueRisk_zero() {
        assertEquals(0, calculator.computeContractValueRisk(0));
    }

    @Test
    @DisplayName("Contract value $30K → 5 risk points (tier 1)")
    void testContractValueRisk_tier1() {
        assertEquals(5, calculator.computeContractValueRisk(30_000));
    }

    @Test
    @DisplayName("Contract value $75K → 10 risk points (tier 2)")
    void testContractValueRisk_tier2() {
        assertEquals(10, calculator.computeContractValueRisk(75_000));
    }

    @Test
    @DisplayName("Contract value $250K → 15 risk points (tier 3)")
    void testContractValueRisk_tier3() {
        assertEquals(15, calculator.computeContractValueRisk(250_000));
    }

    @Test
    @DisplayName("Contract value $500K → 20 risk points (tier 4)")
    void testContractValueRisk_tier4() {
        assertEquals(20, calculator.computeContractValueRisk(500_000));
    }

    @Test
    @DisplayName("Contract value $750K → 25 risk points (tier 5)")
    void testContractValueRisk_tier5() {
        assertEquals(25, calculator.computeContractValueRisk(750_000));
    }

    @Test
    @DisplayName("Contract value $1.5M → 30 risk points (max)")
    void testContractValueRisk_max() {
        assertEquals(30, calculator.computeContractValueRisk(1_500_000));
    }

    // ==================== Liability Risk Tests ====================

    @Test
    @DisplayName("Unlimited liability → 25 risk points")
    void testLiabilityRisk_unlimited() {
        ContractDetails contract = buildContract();
        contract.setLiabilityLimit("unlimited");
        assertEquals(25, calculator.computeLiabilityRisk(contract));
    }

    @Test
    @DisplayName("Capped liability → 0 risk points")
    void testLiabilityRisk_capped() {
        ContractDetails contract = buildContract();
        contract.setLiabilityLimit("$1,000,000.00");
        assertEquals(0, calculator.computeLiabilityRisk(contract));
    }

    @Test
    @DisplayName("Null liability → 25 risk points (treated as unlimited)")
    void testLiabilityRisk_null() {
        ContractDetails contract = buildContract();
        contract.setLiabilityLimit(null);
        assertEquals(25, calculator.computeLiabilityRisk(contract));
    }

    // ==================== Term Duration Risk Tests ====================

    @Test
    @DisplayName("1 year term → 3 risk points")
    void testTermRisk_1year() {
        assertEquals(3, calculator.computeTermDurationRisk(1));
    }

    @Test
    @DisplayName("2 year term → 6 risk points")
    void testTermRisk_2years() {
        assertEquals(6, calculator.computeTermDurationRisk(2));
    }

    @Test
    @DisplayName("6 year term → 15 risk points (max)")
    void testTermRisk_6years() {
        assertEquals(15, calculator.computeTermDurationRisk(6));
    }

    // ==================== Insurance Gap Risk Tests ====================

    @Test
    @DisplayName("Insurance 2x contract value → 0 risk points")
    void testInsuranceRisk_excellent() {
        assertEquals(0, calculator.computeInsuranceGapRisk(250_000, 500_000));
    }

    @Test
    @DisplayName("Insurance 1.5x contract value → 3 risk points")
    void testInsuranceRisk_good() {
        assertEquals(3, calculator.computeInsuranceGapRisk(250_000, 375_000));
    }

    @Test
    @DisplayName("Insurance equals contract value → 6 risk points")
    void testInsuranceRisk_adequate() {
        assertEquals(6, calculator.computeInsuranceGapRisk(250_000, 250_000));
    }

    @Test
    @DisplayName("Insurance 0.5x contract value → 10 risk points")
    void testInsuranceRisk_low() {
        assertEquals(10, calculator.computeInsuranceGapRisk(250_000, 125_000));
    }

    @Test
    @DisplayName("No insurance → 15 risk points")
    void testInsuranceRisk_none() {
        assertEquals(15, calculator.computeInsuranceGapRisk(250_000, 0));
    }

    // ==================== Structural Risk Tests ====================

    @Test
    @DisplayName("Has termination, no auto-renewal → 0 risk points")
    void testStructuralRisk_safe() {
        assertEquals(0, calculator.computeStructuralRisk(true, false));
    }

    @Test
    @DisplayName("Has termination + auto-renewal → 5 risk points")
    void testStructuralRisk_autoRenewal() {
        assertEquals(5, calculator.computeStructuralRisk(true, true));
    }

    @Test
    @DisplayName("No termination, no auto-renewal → 10 risk points")
    void testStructuralRisk_noTermination() {
        assertEquals(10, calculator.computeStructuralRisk(false, false));
    }

    @Test
    @DisplayName("No termination + auto-renewal → 15 risk points (max)")
    void testStructuralRisk_both() {
        assertEquals(15, calculator.computeStructuralRisk(false, true));
    }

    // ==================== Grade Tests ====================

    @Test
    @DisplayName("Score 15 → Grade A")
    void testGrade_A() {
        assertEquals("A", calculator.computeGrade(15));
    }

    @Test
    @DisplayName("Score 35 → Grade B")
    void testGrade_B() {
        assertEquals("B", calculator.computeGrade(35));
    }

    @Test
    @DisplayName("Score 55 → Grade C")
    void testGrade_C() {
        assertEquals("C", calculator.computeGrade(55));
    }

    @Test
    @DisplayName("Score 75 → Grade D")
    void testGrade_D() {
        assertEquals("D", calculator.computeGrade(75));
    }

    @Test
    @DisplayName("Score 95 → Grade F")
    void testGrade_F() {
        assertEquals("F", calculator.computeGrade(95));
    }

    // ==================== Full Integration Tests ====================

    @Test
    @DisplayName("Standard vendor agreement → low risk (grade A or B)")
    void testFullScore_standardVendor() {
        ContractDetails contract = new ContractDetails();
        contract.setContractValue(250_000);
        contract.setContractorName("ACME CLOUD SOLUTIONS");
        contract.setClientName("GFD PLATFORM SYSTEMS");
        contract.setStartDate("2026-06-01");
        contract.setEndDate("2028-06-01");
        contract.setLiabilityLimit("$1,000,000.00");
        contract.setInsuranceCoverage(2_000_000);
        contract.setAutoRenewal(false);
        contract.setHasTerminationClause(true);
        contract.setTermLengthYears(2);

        RiskScore result = calculator.calculate(contract);

        assertNotNull(result);
        // 15 (value) + 0 (liability) + 6 (term) + 0 (insurance 8x) + 0 (structural) = 21
        assertEquals(21, result.getRiskScore());
        assertEquals("B", result.getRiskGrade());
        assertNotNull(result.getRiskBreakdown());
        assertFalse(result.getRecommendations().isEmpty());
        assertNotNull(result.getScoringTimestamp());
    }

    @Test
    @DisplayName("Non-compliant contract → high risk (grade D or F)")
    void testFullScore_nonCompliant() {
        ContractDetails contract = new ContractDetails();
        contract.setContractValue(850_000);
        contract.setContractorName("LEGACY NETWORKS CORP");
        contract.setClientName("GFD PLATFORM SYSTEMS");
        contract.setStartDate("2026-06-01");
        contract.setEndDate("2032-06-01");
        contract.setLiabilityLimit("unlimited liability");
        contract.setInsuranceCoverage(500_000);
        contract.setAutoRenewal(true);
        contract.setHasTerminationClause(false);
        contract.setTermLengthYears(6);

        RiskScore result = calculator.calculate(contract);

        assertNotNull(result);
        // 25 (value) + 25 (liability) + 15 (term) + 10 (ins <1x) + 15 (no term + auto) = 90
        assertEquals(90, result.getRiskScore());
        assertEquals("F", result.getRiskGrade());
        assertTrue(result.getRecommendations().size() >= 3,
                "High-risk contract should have multiple recommendations");
    }

    @Test
    @DisplayName("High-risk liability contract → medium-high risk")
    void testFullScore_highRiskLiability() {
        ContractDetails contract = new ContractDetails();
        contract.setContractValue(450_000);
        contract.setContractorName("APEX DATA SYSTEMS");
        contract.setClientName("GFD PLATFORM SYSTEMS");
        contract.setStartDate("2026-06-01");
        contract.setEndDate("2027-06-01");
        contract.setLiabilityLimit("unlimited liability");
        contract.setInsuranceCoverage(1_500_000);
        contract.setAutoRenewal(false);
        contract.setHasTerminationClause(true);
        contract.setTermLengthYears(1);

        RiskScore result = calculator.calculate(contract);

        assertNotNull(result);
        // 20 (value) + 25 (liability) + 3 (term) + 0 (ins >2x) + 0 (structural) = 48
        assertEquals(48, result.getRiskScore());
        assertEquals("C", result.getRiskGrade());
    }

    // ==================== Helpers ====================

    private ContractDetails buildContract() {
        ContractDetails c = new ContractDetails();
        c.setContractValue(100_000);
        c.setContractorName("Test Vendor");
        c.setClientName("Test Client");
        c.setInsuranceCoverage(200_000);
        c.setHasTerminationClause(true);
        c.setAutoRenewal(false);
        c.setTermLengthYears(1);
        c.setLiabilityLimit("$100,000");
        return c;
    }
}
