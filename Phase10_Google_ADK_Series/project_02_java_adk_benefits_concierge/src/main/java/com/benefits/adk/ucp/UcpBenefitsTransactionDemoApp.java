package com.benefits.adk.ucp;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;
import java.math.BigDecimal;

// Deterministic Module 02 demo. Runs the UCP transaction lane end to end with
// no Gemini call, so it works offline and is safe to screenshot for a post.
//
//   mvn -q compile exec:java \
//     -Dexec.mainClass=com.benefits.adk.ucp.UcpBenefitsTransactionDemoApp
public final class UcpBenefitsTransactionDemoApp {
    private static final ObjectMapper MAPPER = new ObjectMapper().enable(SerializationFeature.INDENT_OUTPUT);

    private UcpBenefitsTransactionDemoApp() {
    }

    public static void main(String[] args) throws Exception {
        UcpBenefitsTransactionService workflow = new UcpBenefitsTransactionService();

        EmployeeProfile newHire = new EmployeeProfile(
                "EMP-1042",
                "Jordan Rivers",
                EmployeeCategory.STANDARD,
                new BigDecimal("90000"),
                "family",
                new BigDecimal("22")
        );

        heading("1. New hire proposes an election (UCP cart)");
        BenefitsTransactionState proposed = workflow.propose(newHire, new BigDecimal("6"), new BigDecimal("6000"), "new-hire-enrollment");
        System.out.println("Status: " + proposed.status());
        printPayslip(proposed.payslipPreview());

        heading("2. Human approval gate — DECLINED path");
        BenefitsTransactionState declined = workflow.approve(proposed, false, null);
        System.out.println("Status: " + declined.status() + "  (nothing submitted)");
        declined.auditTrail().forEach(step -> System.out.println("  - " + step));

        heading("3. Human approval gate — CONFIRMED path -> checkout -> receipt");
        BenefitsTransactionState approved = workflow.approve(proposed, true, "employee confirmed at 6%");
        BenefitsTransactionState enrolled = workflow.checkout(approved);
        System.out.println("Status: " + enrolled.status());
        System.out.println("Confirmation: " + enrolled.receipt().confirmationId()
                + "  Effective: " + enrolled.receipt().effectiveDate());
        enrolled.auditTrail().forEach(step -> System.out.println("  - " + step));

        heading("4. Mock pay statement as validated A2UI");
        Object a2ui = UcpBenefitsTransactionTools.buildPayslipA2ui(
                "Jordan Rivers", "EMP-1042", "standard", 90000, 6, 6000, "family", 22);
        System.out.println(MAPPER.writeValueAsString(a2ui));

        heading("5. Employer match differs by employee category (same 6% deferral, $90k)");
        for (EmployeeCategory category : EmployeeCategory.values()) {
            EmployeeProfile sample = new EmployeeProfile("EMP-" + category, category + " hire",
                    category, new BigDecimal("90000"), "family", new BigDecimal("22"));
            BenefitsTransactionState state = workflow.runToEnrollment(sample, new BigDecimal("6"), new BigDecimal("6000"), "new-hire-enrollment", true);
            System.out.printf("  %-10s match=$%s  savingsEmployerSeed=$%s%n",
                    category,
                    state.projection().employerMatch().toPlainString(),
                    state.plan().savingsEmployerSeed(true).toPlainString());
        }
    }

    private static void printPayslip(Payslip payslip) {
        System.out.println("Pay frequency: " + payslip.payFrequency());
        System.out.println("  Earnings:");
        payslip.earnings().forEach(UcpBenefitsTransactionDemoApp::printLine);
        System.out.println("  Employee deductions (employee):");
        payslip.employeeDeductions().forEach(UcpBenefitsTransactionDemoApp::printLine);
        System.out.println("  Employer contributions:");
        payslip.employerContributions().forEach(UcpBenefitsTransactionDemoApp::printLine);
        System.out.println("  Adjusted base per period: $" + payslip.adjustedBasePerPeriod().toPlainString());
    }

    private static void printLine(Payslip.Line line) {
        System.out.printf("    %-32s per period $%-10s annual $%s%n",
                line.label(), line.perPeriod().toPlainString(), line.annual().toPlainString());
    }

    private static void heading(String title) {
        System.out.println();
        System.out.println("== " + title + " ==");
    }
}
