package com.benefits.adk.ucp;

import com.benefits.adk.tools.ContributionProjection;
import com.benefits.adk.tools.ContributionProjectionService;
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.ArrayList;
import java.util.List;

// The Module 02 "dynamic workflow": a UCP-shaped benefits transaction lane.
//
//   propose(...)  -> PENDING_APPROVAL   (cart + projection + payslip preview)
//   approve(...)  -> APPROVED | BLOCKED (explicit human gate)
//   checkout(...) -> ENROLLED  | BLOCKED (order/receipt = mock pay statement)
//
// All numbers are fictional; "ENROLLED" records nothing in a real system.
public final class UcpBenefitsTransactionService {
    private static final String HUNDRED = "100";

    private final BenefitsPlanCatalog catalog;
    private final PayslipService payslipService;

    public UcpBenefitsTransactionService() {
        this(new BenefitsPlanCatalog(), new PayslipService());
    }

    public UcpBenefitsTransactionService(BenefitsPlanCatalog catalog, PayslipService payslipService) {
        this.catalog = catalog;
        this.payslipService = payslipService;
    }

    // Step 1: look up the plan for the employee's category, build the proposed
    // election, project the numbers, and stage a payslip preview.
    public BenefitsTransactionState propose(
            EmployeeProfile employee,
            BigDecimal requestedPrimaryPercent,
            BigDecimal requestedAnnualSavings,
            String electionType
    ) {
        BenefitsPlanOption plan = catalog.lookup(employee.category());
        ProposedElection election = new ProposedElection(
                electionType,
                requestedPrimaryPercent == null ? BigDecimal.ZERO : requestedPrimaryPercent,
                requestedAnnualSavings == null ? BigDecimal.ZERO : requestedAnnualSavings,
                employee.coverageType()
        );
        ContributionProjection projection = project(employee, plan, election);
        Payslip preview = payslipService.buildPreview(employee, plan, projection);

        String transactionId = "TXN-" + employee.employeeId();
        BenefitsTransactionState proposed = new BenefitsTransactionState(
                transactionId,
                TransactionStatus.PROPOSED,
                employee,
                plan,
                election,
                projection,
                preview,
                null,
                List.of("PROPOSED: drafted " + plan.planName() + " election for " + employee.fullName())
        );
        return proposed.with(TransactionStatus.PENDING_APPROVAL, "awaiting explicit human confirmation before any submission");
    }

    // Step 2: the human-approval gate. Nothing is submitted without an explicit
    // confirmation; a decline is a terminal BLOCKED state.
    public BenefitsTransactionState approve(BenefitsTransactionState state, boolean humanConfirmed, String approverNote) {
        if (state.status() != TransactionStatus.PENDING_APPROVAL) {
            return state.with(TransactionStatus.BLOCKED, "approval is only valid from PENDING_APPROVAL, not " + state.status());
        }
        if (!humanConfirmed) {
            return state.with(TransactionStatus.BLOCKED, "human confirmation was not given; nothing was submitted");
        }
        String note = approverNote == null || approverNote.isBlank() ? "employee confirmed the election" : approverNote.trim();
        return state.with(TransactionStatus.APPROVED, note);
    }

    // Step 3: checkout. Requires an APPROVED state; produces the order/receipt.
    public BenefitsTransactionState checkout(BenefitsTransactionState state) {
        if (state.status() != TransactionStatus.APPROVED) {
            return state.with(TransactionStatus.BLOCKED, "checkout requires an APPROVED transaction; current status is " + state.status());
        }
        List<String> receiptNotes = new ArrayList<>();
        receiptNotes.add("Fictional educational enrollment. No real election, account, or record system record was created.");
        receiptNotes.add("Plan: " + state.plan().planName() + " — match: " + state.plan().matchDescription());

        EnrollmentReceipt receipt = new EnrollmentReceipt(
                "ENR-" + state.employee().employeeId(),
                "next semi-monthly pay cycle (fictional)",
                state.payslipPreview(),
                List.copyOf(receiptNotes)
        );
        return state.withReceipt(receipt, "fictional enrollment recorded; confirmation " + receipt.confirmationId());
    }

    // Convenience: run the whole lane. A false approval stops at BLOCKED after
    // the gate, exactly like a user declining the confirmation.
    public BenefitsTransactionState runToEnrollment(
            EmployeeProfile employee,
            BigDecimal requestedPrimaryPercent,
            BigDecimal requestedAnnualSavings,
            String electionType,
            boolean humanApproved
    ) {
        BenefitsTransactionState proposed = propose(employee, requestedPrimaryPercent, requestedAnnualSavings, electionType);
        BenefitsTransactionState approved = approve(proposed, humanApproved, null);
        if (approved.status() != TransactionStatus.APPROVED) {
            return approved;
        }
        return checkout(approved);
    }

    // Category-aware projection with 2026 fixture caps applied deterministically.
    private ContributionProjection project(EmployeeProfile employee, BenefitsPlanOption plan, ProposedElection election) {
        BigDecimal salary = requireNonNegative(employee.annualSalary(), "annualSalary");
        BigDecimal percent = requireNonNegative(election.employeePrimaryPercent(), "employeePrimaryPercent");
        BigDecimal requestedAnnualSavings = requireNonNegative(election.annualSavingsContribution(), "annualSavingsContribution");
        BigDecimal adjustmentRate = requireNonNegative(employee.adjustmentRatePercent(), "adjustmentRatePercent");

        BigDecimal employeePrimary = salary.multiply(percent).divide(new BigDecimal(HUNDRED), 8, RoundingMode.HALF_UP);
        BigDecimal cappedEmployeeprimary = employeePrimary.min(ContributionProjectionService.EMPLOYEE_PRIMARY_LIMIT_2026);
        BigDecimal rawEmployerMatch = plan.employerMatch(salary, percent);
        BigDecimal employerMatch = capEmployerMatch(cappedEmployeeprimary, rawEmployerMatch);
        BigDecimal combined = cappedEmployeeprimary.add(employerMatch);

        boolean family = employee.familyCoverage();
        BigDecimal savingsLimit = family
                ? ContributionProjectionService.SAVINGS_FAMILY_LIMIT_2026
                : ContributionProjectionService.SAVINGS_SELF_ONLY_LIMIT_2026;
        BigDecimal employerSeed = plan.savingsEmployerSeed(family);
        BigDecimal maxEmployeeSavings = savingsLimit.subtract(employerSeed).max(BigDecimal.ZERO);
        BigDecimal cappedSavings = requestedAnnualSavings.min(maxEmployeeSavings);

        BigDecimal savingsAdjustment = cappedSavings
                .multiply(adjustmentRate)
                .divide(new BigDecimal(HUNDRED), 8, RoundingMode.HALF_UP);

        List<String> notes = new ArrayList<>();
        notes.add("Fictional educational estimate; not professional advice.");
        notes.add(plan.planName() + " match: " + plan.matchDescription());
        if (employeePrimary.compareTo(ContributionProjectionService.EMPLOYEE_PRIMARY_LIMIT_2026) > 0) {
            notes.add("Employee primary contribution contribution was capped at the 2026 learning limit of $24,500.");
        }
        if (rawEmployerMatch.compareTo(employerMatch) > 0) {
            notes.add("Employer match was reduced so employee + employer contributions stay within the 2026 learning limit of $72,000.");
        }
        if (requestedAnnualSavings.compareTo(cappedSavings) > 0) {
            notes.add("Employee savings account was reduced so the employee + employer seed stays within the "
                    + (family ? "family" : "self-only") + " savings account limit.");
        }

        return new ContributionProjection(
                salary,
                cappedEmployeeprimary,
                employerMatch,
                combined,
                cappedSavings,
                savingsAdjustment,
                List.copyOf(notes)
        ).rounded();
    }

    private static BigDecimal capEmployerMatch(BigDecimal cappedEmployeeprimary, BigDecimal rawEmployerMatch) {
        BigDecimal remainingCombinedRoom = ContributionProjectionService.COMBINED_PRIMARY_LIMIT_2026
                .subtract(cappedEmployeeprimary)
                .max(BigDecimal.ZERO);
        return rawEmployerMatch.min(remainingCombinedRoom);
    }

    private static BigDecimal requireNonNegative(BigDecimal value, String fieldName) {
        BigDecimal resolved = value == null ? BigDecimal.ZERO : value;
        if (resolved.compareTo(BigDecimal.ZERO) < 0) {
            throw new IllegalArgumentException(fieldName + " must be non-negative");
        }
        return resolved;
    }
}
