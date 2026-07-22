package com.example.taskcredentials;

import java.math.BigDecimal;
import java.util.Map;
import org.springframework.http.HttpStatus;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

@RestController
public class InvoiceController {
    private static final Map<String, Invoice> INVOICES = Map.of(
            "inv-acme-001", new Invoice(
                    "inv-acme-001", "fictional-acme", "Fictional Office Supply Co.",
                    new BigDecimal("125.00"), "USD", "OPEN"),
            "inv-globex-001", new Invoice(
                    "inv-globex-001", "fictional-globex", "Imaginary Cloud Hosting LLC",
                    new BigDecimal("480.00"), "USD", "REVIEW"));

    private final AgentStatusClient agentStatusClient;

    public InvoiceController(AgentStatusClient agentStatusClient) {
        this.agentStatusClient = agentStatusClient;
    }

    @GetMapping("/fictional-invoices/{invoiceId}")
    @PreAuthorize("hasAuthority('SCOPE_invoice.read')")
    InvoiceResponse invoice(@PathVariable String invoiceId, @AuthenticationPrincipal Jwt jwt) {
        Invoice invoice = INVOICES.get(invoiceId);
        if (invoice == null) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "Fictional invoice not found");
        }
        if (!"task".equals(jwt.getClaimAsString("credential_type"))) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "A task credential is required");
        }
        String taskId = jwt.getClaimAsString("task_id");
        String agentId = jwt.getClaimAsString("agent_id");
        if (taskId == null || taskId.isBlank() || agentId == null || agentId.isBlank()) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "Task and agent context are required");
        }
        if (!invoice.tenantId().equals(jwt.getClaimAsString("tenant_id"))) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "Tenant boundary denied this resource");
        }
        if (!agentStatusClient.isActive(agentId)) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "Agent is revoked or status is unavailable");
        }
        if (!agentStatusClient.isTaskActive(taskId, agentId)) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "Task is expired, revoked, or unavailable");
        }
        return new InvoiceResponse(
                invoice.id(), invoice.tenantId(), invoice.vendor(), invoice.amount(),
                invoice.currency(), invoice.status(), taskId, jwt.getClaimAsString("audit_id"));
    }

    record Invoice(String id, String tenantId, String vendor, BigDecimal amount, String currency, String status) {}

    record InvoiceResponse(
            String id,
            String tenantId,
            String vendor,
            BigDecimal amount,
            String currency,
            String status,
            String taskId,
            String auditId) {}
}
