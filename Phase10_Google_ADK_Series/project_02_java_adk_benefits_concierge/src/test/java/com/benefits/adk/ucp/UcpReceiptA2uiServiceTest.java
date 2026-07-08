package com.benefits.adk.ucp;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.benefits.adk.ui.A2uiPayload;
import java.math.BigDecimal;
import java.util.Map;
import org.junit.jupiter.api.Test;

class UcpReceiptA2uiServiceTest {
    private final UcpBenefitsTransactionService workflow = new UcpBenefitsTransactionService();
    private final UcpReceiptA2uiService receiptA2ui = new UcpReceiptA2uiService();

    private BenefitsTransactionState enrolledState() {
        EmployeeProfile employee = new EmployeeProfile("EMP-1042", "Jordan Rivers", EmployeeCategory.STANDARD,
                new BigDecimal("90000"), "family", new BigDecimal("22"));
        return workflow.runToEnrollment(employee, new BigDecimal("6"), new BigDecimal("6000"), "new-hire-enrollment", true);
    }

    @Test
    void payslipReceiptIsAValidatedTrustedCatalogCard() {
        A2uiPayload payload = receiptA2ui.payslipReceipt(enrolledState());

        assertEquals("a2ui.phase10.module02.v1", payload.schemaVersion());
        assertEquals("Card", payload.root().type());
        assertTrue(payload.validation().valid());
        long tableCount = payload.root().children().stream()
                .filter(child -> "Table".equals(child.type()))
                .count();
        assertEquals(3, tableCount);
    }

    @Test
    void exposedToolReturnsA2uiDataPartShape() {
        Map<String, Object> payload = UcpBenefitsTransactionTools.buildPayslipA2ui(
                "Jordan Rivers", "EMP-1042", "standard", 90000, 6, 6000, "family", 22);

        @SuppressWarnings("unchecked")
        Map<String, Object> metadata = (Map<String, Object>) payload.get("metadata");
        @SuppressWarnings("unchecked")
        Map<String, Object> data = (Map<String, Object>) payload.get("data");
        @SuppressWarnings("unchecked")
        Map<String, Object> root = (Map<String, Object>) data.get("root");
        @SuppressWarnings("unchecked")
        Map<String, Object> validation = (Map<String, Object>) data.get("validation");

        assertEquals("application/json+a2ui", metadata.get("mimeType"));
        assertEquals("a2ui.phase10.module02.v1", data.get("schemaVersion"));
        assertEquals("Card", root.get("type"));
        assertEquals(true, validation.get("valid"));
        assertTrue(root.toString().contains("PENDING_APPROVAL"));
        assertTrue(root.toString().contains("(not enrolled)"));
    }

    @Test
    void blockedTransactionHasNoConfirmation() {
        EmployeeProfile employee = new EmployeeProfile("EMP-1042", "Jordan Rivers", EmployeeCategory.STANDARD,
                new BigDecimal("90000"), "family", new BigDecimal("22"));
        BenefitsTransactionState blocked = workflow.runToEnrollment(
                employee, new BigDecimal("6"), new BigDecimal("6000"), "new-hire-enrollment", false);

        A2uiPayload payload = receiptA2ui.payslipReceipt(blocked);

        assertTrue(payload.validation().valid());
        assertTrue(payload.root().children().stream()
                .anyMatch(child -> "Text".equals(child.type())
                        && String.valueOf(child.props().get("text")).contains("BLOCKED")));
    }
}
