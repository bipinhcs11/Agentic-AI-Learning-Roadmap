package com.benefits.adk.ucp;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.math.BigDecimal;
import org.junit.jupiter.api.Test;

class UcpBenefitsTransactionServiceTest {
    private final UcpBenefitsTransactionService workflow = new UcpBenefitsTransactionService();

    private static EmployeeProfile standardNewHire() {
        return new EmployeeProfile("EMP-1042", "Jordan Rivers", EmployeeCategory.STANDARD,
                new BigDecimal("90000"), "family", new BigDecimal("22"));
    }

    @Test
    void proposeStagesElectionWithCategoryAwareMatch() {
        BenefitsTransactionState state = workflow.propose(
                standardNewHire(), new BigDecimal("6"), new BigDecimal("6000"), "new-hire-enrollment");

        assertEquals(TransactionStatus.PENDING_APPROVAL, state.status());
        assertEquals(new BigDecimal("5400.00"), state.projection().employeePrimaryContribution());
        assertEquals(new BigDecimal("4050.00"), state.projection().employerMatch());
        assertEquals(new BigDecimal("9450.00"), state.projection().combinedPrimaryContribution());
        assertEquals(new BigDecimal("6000.00"), state.projection().savingsContribution());
        assertEquals(new BigDecimal("1320.00"), state.projection().estimatedSavingsAdjustment());
        assertNull(state.receipt());
    }

    @Test
    void decliningApprovalBlocksAndSubmitsNothing() {
        BenefitsTransactionState blocked = workflow.runToEnrollment(
                standardNewHire(), new BigDecimal("6"), new BigDecimal("6000"), "new-hire-enrollment", false);

        assertEquals(TransactionStatus.BLOCKED, blocked.status());
        assertNull(blocked.receipt());
        assertTrue(blocked.auditTrail().stream().anyMatch(step -> step.contains("human confirmation was not given")));
    }

    @Test
    void checkoutRequiresAnApprovedState() {
        BenefitsTransactionState proposed = workflow.propose(
                standardNewHire(), new BigDecimal("6"), new BigDecimal("6000"), "new-hire-enrollment");

        BenefitsTransactionState blocked = workflow.checkout(proposed);

        assertEquals(TransactionStatus.BLOCKED, blocked.status());
        assertNull(blocked.receipt());
    }

    @Test
    void confirmedFlowEnrollsAndProducesReceipt() {
        BenefitsTransactionState enrolled = workflow.runToEnrollment(
                standardNewHire(), new BigDecimal("6"), new BigDecimal("6000"), "new-hire-enrollment", true);

        assertEquals(TransactionStatus.ENROLLED, enrolled.status());
        assertNotNull(enrolled.receipt());
        assertEquals("ENR-EMP-1042", enrolled.receipt().confirmationId());
        assertNotNull(enrolled.receipt().payslip());
    }

    @Test
    void employeeSavingsIsReducedToStayWithinTheFamilyLimit() {
        BenefitsTransactionState state = workflow.propose(
                standardNewHire(), new BigDecimal("6"), new BigDecimal("9000"), "new-hire-enrollment");

        // Family limit 8750 minus a 1000 employer seed leaves 7750 of room.
        assertEquals(new BigDecimal("7750.00"), state.projection().savingsContribution());
        assertTrue(state.projection().notes().stream().anyMatch(note -> note.contains("reduced")));
    }

    @Test
    void employerMatchIsReducedWhenCombinedFixtureLimitWouldBeExceeded() {
        EmployeeProfile executive = new EmployeeProfile("EMP-9999", "Executive Hire", EmployeeCategory.EXECUTIVE,
                new BigDecimal("2000000"), "family", new BigDecimal("22"));

        BenefitsTransactionState state = workflow.propose(
                executive, new BigDecimal("6"), new BigDecimal("6000"), "new-hire-enrollment");

        assertEquals(new BigDecimal("24500.00"), state.projection().employeePrimaryContribution());
        assertEquals(new BigDecimal("47500.00"), state.projection().employerMatch());
        assertEquals(new BigDecimal("72000.00"), state.projection().combinedPrimaryContribution());
        assertTrue(state.projection().notes().stream().anyMatch(note -> note.contains("Employer match was reduced")));
    }
}
