package com.benefits.adk.ucp;

import com.benefits.adk.tools.ContributionProjection;
import java.util.ArrayList;
import java.util.List;

// The immutable state passed between workflow steps. Each transition returns a
// new state with an appended audit entry, so the whole propose -> approve ->
// checkout history is observable (important for a transaction lane).
public record BenefitsTransactionState(
        String transactionId,
        TransactionStatus status,
        EmployeeProfile employee,
        BenefitsPlanOption plan,
        ProposedElection election,
        ContributionProjection projection,
        Payslip payslipPreview,
        EnrollmentReceipt receipt,
        List<String> auditTrail
) {
    public BenefitsTransactionState {
        auditTrail = auditTrail == null ? List.of() : List.copyOf(auditTrail);
    }

    // Build the next state, carrying everything forward and recording the step.
    public BenefitsTransactionState with(TransactionStatus nextStatus, String auditEntry) {
        List<String> nextTrail = new ArrayList<>(auditTrail);
        nextTrail.add(nextStatus + ": " + auditEntry);
        return new BenefitsTransactionState(
                transactionId, nextStatus, employee, plan, election,
                projection, payslipPreview, receipt, List.copyOf(nextTrail)
        );
    }

    public BenefitsTransactionState withReceipt(EnrollmentReceipt enrollmentReceipt, String auditEntry) {
        List<String> nextTrail = new ArrayList<>(auditTrail);
        nextTrail.add(TransactionStatus.ENROLLED + ": " + auditEntry);
        return new BenefitsTransactionState(
                transactionId, TransactionStatus.ENROLLED, employee, plan, election,
                projection, payslipPreview, enrollmentReceipt, List.copyOf(nextTrail)
        );
    }

    public boolean enrolled() {
        return status == TransactionStatus.ENROLLED;
    }

    public boolean blocked() {
        return status == TransactionStatus.BLOCKED;
    }
}
