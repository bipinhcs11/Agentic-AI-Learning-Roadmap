package com.benefits.adk.ucp;

import com.benefits.adk.tools.ContributionProjection;
import com.benefits.adk.ui.A2uiComponent;
import com.benefits.adk.ui.A2uiPayload;
import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

// Stateless ADK tool facade over the transaction workflow. The agent calls
// previewEnrollment first (PENDING_APPROVAL), then submitEnrollment only after
// the human confirms. submitEnrollment refuses to enroll without humanApproved,
// which is how the approval gate is enforced in a stateless tool world.
public final class UcpBenefitsTransactionTools {
    private static final UcpBenefitsTransactionService WORKFLOW = new UcpBenefitsTransactionService();
    private static final UcpReceiptA2uiService RECEIPT_A2UI = new UcpReceiptA2uiService();

    private UcpBenefitsTransactionTools() {
    }

    // Step 1 for the agent: draft + project + preview, but do not submit.
    public static Map<String, Object> previewEnrollment(
            String employeeName,
            String employeeId,
            String category,
            double annualSalary,
            double employeePrimaryPercent,
            double annualSavingsContribution,
            String coverageType,
            double adjustmentRate
    ) {
        EmployeeProfile employee = profile(employeeName, employeeId, category, annualSalary, coverageType, adjustmentRate);
        BenefitsTransactionState state = WORKFLOW.propose(
                employee,
                BigDecimal.valueOf(employeePrimaryPercent),
                BigDecimal.valueOf(annualSavingsContribution),
                "new-hire-enrollment"
        );
        Map<String, Object> result = summarize(state);
        result.put("approvalSteps", List.of(
                "Review the fictional pay statement preview.",
                "Confirm the primary contribution percent and savings account amount are what you want.",
                "Call submitEnrollment with humanApproved=true to record the fictional enrollment."
        ));
        return result;
    }

    // Step 2 for the agent: submit only with an explicit human approval.
    public static Map<String, Object> submitEnrollment(
            String employeeName,
            String employeeId,
            String category,
            double annualSalary,
            double employeePrimaryPercent,
            double annualSavingsContribution,
            String coverageType,
            double adjustmentRate,
            boolean humanApproved
    ) {
        EmployeeProfile employee = profile(employeeName, employeeId, category, annualSalary, coverageType, adjustmentRate);
        BenefitsTransactionState state = WORKFLOW.runToEnrollment(
                employee,
                BigDecimal.valueOf(employeePrimaryPercent),
                BigDecimal.valueOf(annualSavingsContribution),
                "new-hire-enrollment",
                humanApproved
        );
        Map<String, Object> result = summarize(state);
        if (state.receipt() != null) {
            result.put("receipt", Map.of(
                    "confirmationId", state.receipt().confirmationId(),
                    "effectiveDate", state.receipt().effectiveDate(),
                    "notes", state.receipt().notes()
            ));
        }
        return result;
    }

    // The renderable mock pay statement as a validated A2UI payload.
    public static Map<String, Object> buildPayslipA2ui(
            String employeeName,
            String employeeId,
            String category,
            double annualSalary,
            double employeePrimaryPercent,
            double annualSavingsContribution,
            String coverageType,
            double adjustmentRate
    ) {
        EmployeeProfile employee = profile(employeeName, employeeId, category, annualSalary, coverageType, adjustmentRate);
        BenefitsTransactionState state = WORKFLOW.propose(
                employee,
                BigDecimal.valueOf(employeePrimaryPercent),
                BigDecimal.valueOf(annualSavingsContribution),
                "new-hire-enrollment"
        );
        A2uiPayload payload = RECEIPT_A2UI.payslipReceipt(state);
        return Map.of(
                "data", Map.of(
                        "schemaVersion", payload.schemaVersion(),
                        "root", componentToMap(payload.root()),
                        "validation", Map.of(
                                "valid", payload.validation().valid(),
                                "errors", payload.validation().errors()
                        )
                ),
                "metadata", Map.of(
                        "mimeType", "application/json+a2ui",
                        "module", "02",
                        "trustedCatalog", List.of("Card", "Table", "Text")
                )
        );
    }

    private static EmployeeProfile profile(
            String employeeName,
            String employeeId,
            String category,
            double annualSalary,
            String coverageType,
            double adjustmentRate
    ) {
        return new EmployeeProfile(
                employeeId,
                employeeName,
                EmployeeCategory.fromLabel(category),
                BigDecimal.valueOf(annualSalary),
                coverageType,
                BigDecimal.valueOf(adjustmentRate)
        );
    }

    private static Map<String, Object> summarize(BenefitsTransactionState state) {
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("transactionId", state.transactionId());
        result.put("status", state.status().name());
        result.put("plan", state.plan().planName());
        result.put("matchDescription", state.plan().matchDescription());
        result.put("projection", projectionMap(state.projection()));
        result.put("payslip", payslipMap(state.payslipPreview()));
        result.put("auditTrail", state.auditTrail());
        return result;
    }

    private static Map<String, Object> projectionMap(ContributionProjection projection) {
        Map<String, Object> map = new LinkedHashMap<>();
        map.put("annualSalary", projection.annualSalary().toPlainString());
        map.put("employeePrimary", projection.employeePrimaryContribution().toPlainString());
        map.put("employerMatch", projection.employerMatch().toPlainString());
        map.put("combinedPrimary", projection.combinedPrimaryContribution().toPlainString());
        map.put("savingsContribution", projection.savingsContribution().toPlainString());
        map.put("estimatedSavingsAdjustment", projection.estimatedSavingsAdjustment().toPlainString());
        map.put("notes", projection.notes());
        return map;
    }

    private static Map<String, Object> payslipMap(Payslip payslip) {
        Map<String, Object> map = new LinkedHashMap<>();
        map.put("payFrequency", payslip.payFrequency());
        map.put("periodsPerYear", payslip.periodsPerYear());
        map.put("earnings", lines(payslip.earnings()));
        map.put("employeeDeductions", lines(payslip.employeeDeductions()));
        map.put("employerContributions", lines(payslip.employerContributions()));
        map.put("adjustedBasePerPeriod", payslip.adjustedBasePerPeriod().toPlainString());
        map.put("notes", payslip.notes());
        return map;
    }

    private static List<Map<String, Object>> lines(List<Payslip.Line> lines) {
        List<Map<String, Object>> mapped = new ArrayList<>();
        for (Payslip.Line line : lines) {
            Map<String, Object> row = new LinkedHashMap<>();
            row.put("label", line.label());
            row.put("perPeriod", line.perPeriod().toPlainString());
            row.put("annual", line.annual().toPlainString());
            mapped.add(row);
        }
        return mapped;
    }

    private static Map<String, Object> componentToMap(A2uiComponent component) {
        return Map.of(
                "type", component.type(),
                "props", component.props(),
                "children", component.children().stream()
                        .map(UcpBenefitsTransactionTools::componentToMap)
                        .toList()
        );
    }
}
