package com.example.securemcp;

import java.math.BigDecimal;
import java.util.Map;
import java.util.Set;
import org.springaicommunity.mcp.annotation.McpTool;
import org.springaicommunity.mcp.annotation.McpToolParam;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Component;
import org.springframework.web.server.ResponseStatusException;

@Component
class SecureEnterpriseTools {
    private static final Map<String, Invoice> INVOICES = Map.of(
            "inv-acme-001", new Invoice(
                    "inv-acme-001", "fictional-acme", "Fictional Office Supply Co.",
                    new BigDecimal("125.00"), "USD", "OPEN"),
            "inv-globex-001", new Invoice(
                    "inv-globex-001", "fictional-globex", "Imaginary Cloud Hosting LLC",
                    new BigDecimal("480.00"), "USD", "REVIEW"));

    private final ToolAuthorizer authorizer;

    SecureEnterpriseTools(ToolAuthorizer authorizer) {
        this.authorizer = authorizer;
    }

    @McpTool(
            name = "get_fictional_invoice",
            description = "Read one tenant-scoped fictional invoice. Requires invoice.read.",
            generateOutputSchema = true)
    InvoiceResult getFictionalInvoice(
            @McpToolParam(description = "Fictional invoice id.", required = true) String invoiceId) {
        Invoice invoice = INVOICES.get(invoiceId);
        if (invoice == null) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "Fictional invoice not found");
        }
        ToolAuthorizer.SecurityContext context = authorizer.authorize(
                "get_fictional_invoice", Set.of("invoice.read"), invoice.tenantId());
        return new InvoiceResult(
                invoice.id(), invoice.tenantId(), invoice.vendor(), invoice.amount(),
                invoice.currency(), invoice.status(), context.taskId(), context.auditId());
    }

    @McpTool(
            name = "draft_fictional_email",
            description = "Create an in-memory fictional email draft. It never sends. Requires email.draft.",
            generateOutputSchema = true)
    EmailDraft draftFictionalEmail(
            @McpToolParam(description = "Recipient at example.invalid.", required = true) String recipient,
            @McpToolParam(description = "Draft subject.", required = true) String subject,
            @McpToolParam(description = "Draft body.", required = true) String body) {
        ToolAuthorizer.SecurityContext context = authorizer.authorize(
                "draft_fictional_email", Set.of("email.draft"), null);
        if (recipient == null || !recipient.endsWith("@example.invalid")) {
            throw new ResponseStatusException(
                    HttpStatus.BAD_REQUEST,
                    "The educational tool only accepts example.invalid recipients");
        }
        return new EmailDraft(
                "draft-" + context.taskId(), recipient, subject, body,
                "DRAFT_ONLY_NOT_SENT", context.taskId(), context.auditId());
    }

    record Invoice(String id, String tenantId, String vendor, BigDecimal amount, String currency, String status) {}
    record InvoiceResult(
            String id, String tenantId, String vendor, BigDecimal amount, String currency,
            String status, String taskId, String auditId) {}
    record EmailDraft(
            String id, String recipient, String subject, String body, String status,
            String taskId, String auditId) {}
}
