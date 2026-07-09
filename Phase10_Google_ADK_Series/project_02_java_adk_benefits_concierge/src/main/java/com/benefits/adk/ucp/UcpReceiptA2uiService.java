package com.benefits.adk.ucp;

import com.benefits.adk.ui.A2uiComponent;
import com.benefits.adk.ui.A2uiPayload;
import com.benefits.adk.ui.A2uiValidationResult;
import com.benefits.adk.ui.TrustedA2uiCatalog;
import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

// Renders the enrollment receipt as a mock pay statement using only the
// trusted A2UI catalog (Card / Table / Text). The whole payslip UI is
// described declaratively so the React renderer (Rung 01C) can draw it, and
// it is validated server-side before it would ever be sent.
public final class UcpReceiptA2uiService {
    public static final String SCHEMA_VERSION = "a2ui.phase10.module02.v1";

    private final TrustedA2uiCatalog catalog;

    public UcpReceiptA2uiService() {
        this(new TrustedA2uiCatalog());
    }

    UcpReceiptA2uiService(TrustedA2uiCatalog catalog) {
        this.catalog = catalog;
    }

    public A2uiPayload payslipReceipt(BenefitsTransactionState state) {
        EmployeeProfile employee = state.employee();
        Payslip payslip = state.payslipPreview();
        EnrollmentReceipt receipt = state.receipt();

        String confirmation = receipt == null ? "(not enrolled)" : receipt.confirmationId();
        String effectiveDate = receipt == null ? "(pending approval)" : receipt.effectiveDate();

        List<A2uiComponent> children = new ArrayList<>();
        children.add(text("Employee: " + employee.fullName()
                + "  |  Category: " + employee.category()
                + "  |  Status: " + state.status()));
        children.add(text("Confirmation: " + confirmation + "  |  Effective: " + effectiveDate));
        children.add(text("Pay frequency: " + payslip.payFrequency()));
        // Section titles are Text nodes, and Tables carry only columns/rows, so
        // the payload also passes the stricter React renderer prop allowlist.
        children.add(text("Earnings"));
        children.add(lineTable(payslip.earnings()));
        children.add(text("Employee deductions (employee)"));
        children.add(lineTable(payslip.employeeDeductions()));
        children.add(text("Employer contributions"));
        children.add(lineTable(payslip.employerContributions()));
        children.add(text("Adjusted base per period: $" + payslip.adjustedBasePerPeriod().toPlainString()
                + "  |  Estimated annual savings adjustment: $" + payslip.estimatedAnnualSavingsAdjustment().toPlainString()));
        for (String note : payslip.notes()) {
            children.add(text(note));
        }

        A2uiComponent card = new A2uiComponent(
                "Card",
                Map.of("title", "Fictional pay statement preview"),
                children
        );
        A2uiValidationResult validation = catalog.validate(card);
        return new A2uiPayload(SCHEMA_VERSION, card, validation);
    }

    private static A2uiComponent text(String value) {
        return new A2uiComponent("Text", Map.of("text", value), List.of());
    }

    private static A2uiComponent lineTable(List<Payslip.Line> lines) {
        List<List<String>> rows = new ArrayList<>();
        for (Payslip.Line line : lines) {
            rows.add(List.of(
                    line.label(),
                    "$" + safe(line.perPeriod()),
                    "$" + safe(line.annual())
            ));
        }
        return new A2uiComponent(
                "Table",
                Map.of(
                        "columns", List.of("Item", "Per pay period", "Annual"),
                        "rows", rows
                ),
                List.of()
        );
    }

    private static String safe(BigDecimal value) {
        return (value == null ? BigDecimal.ZERO : value).toPlainString();
    }
}
