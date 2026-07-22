package com.example.securemcp;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.time.Instant;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.security.oauth2.server.resource.authentication.JwtAuthenticationToken;
import org.springframework.web.server.ResponseStatusException;

class SecureEnterpriseToolsTest {
    private final AuditService audit = new AuditService();
    private final ToolAuthorizer authorizer = new ToolAuthorizer(audit, (agent, task) -> true, 2);
    private final SecureEnterpriseTools tools = new SecureEnterpriseTools(authorizer);

    @AfterEach
    void clearSecurityContext() {
        SecurityContextHolder.clearContext();
    }

    @Test
    void allowsScopedToolWithinTenant() {
        authenticate("invoice.read", "fictional-acme", "task-1", "task", 1);
        var result = tools.getFictionalInvoice("inv-acme-001");
        assertThat(result.id()).isEqualTo("inv-acme-001");
        assertThat(result.auditId()).isEqualTo("audit-1");
        assertThat(audit.recent().getFirst().decision()).isEqualTo("ALLOW");
    }

    @Test
    void deniesWrongToolScopeAndCrossTenantRead() {
        authenticate("email.draft", "fictional-acme", "task-1", "task", 1);
        assertThatThrownBy(() -> tools.getFictionalInvoice("inv-acme-001"))
                .isInstanceOf(ResponseStatusException.class)
                .hasMessageContaining("scope allow-list");

        authenticate("invoice.read", "fictional-acme", "task-1", "task", 1);
        assertThatThrownBy(() -> tools.getFictionalInvoice("inv-globex-001"))
                .isInstanceOf(ResponseStatusException.class)
                .hasMessageContaining("Tenant boundary");
    }

    @Test
    void requiresTaskCredentialAndBoundedDelegation() {
        authenticate("email.draft", "fictional-acme", "task-1", "agent", 0);
        assertThatThrownBy(() -> tools.draftFictionalEmail(
                "demo@example.invalid", "Subject", "Body"))
                .isInstanceOf(ResponseStatusException.class)
                .hasMessageContaining("task credential");

        authenticate("email.draft", "fictional-acme", "task-1", "task", 3);
        assertThatThrownBy(() -> tools.draftFictionalEmail(
                "demo@example.invalid", "Subject", "Body"))
                .isInstanceOf(ResponseStatusException.class)
                .hasMessageContaining("depth");
    }

    @Test
    void emailToolCreatesDraftForReservedDomainOnly() {
        authenticate("email.draft", "fictional-acme", "task-2", "task", 1);
        var draft = tools.draftFictionalEmail("demo@example.invalid", "Hello", "Fictional body");
        assertThat(draft.status()).isEqualTo("DRAFT_ONLY_NOT_SENT");
        assertThatThrownBy(() -> tools.draftFictionalEmail("person@example.com", "Hello", "Body"))
                .isInstanceOf(ResponseStatusException.class)
                .hasMessageContaining("example.invalid");
    }

    @Test
    void failsClosedWhenTaskStatusCannotBeConfirmed() {
        ToolAuthorizer failClosed = new ToolAuthorizer(audit, (agent, task) -> false, 2);
        SecureEnterpriseTools protectedTools = new SecureEnterpriseTools(failClosed);
        authenticate("invoice.read", "fictional-acme", "task-3", "task", 1);
        assertThatThrownBy(() -> protectedTools.getFictionalInvoice("inv-acme-001"))
                .isInstanceOf(ResponseStatusException.class)
                .hasMessageContaining("revoked, expired, or unavailable");
    }

    private void authenticate(
            String scope, String tenant, String taskId, String credentialType, int depth) {
        Instant now = Instant.now();
        Jwt jwt = new Jwt(
                "test-token",
                now,
                now.plusSeconds(600),
                Map.of("alg", "RS256"),
                Map.of(
                        "sub", "agent:test",
                        "aud", List.of("http://localhost:8086/mcp"),
                        "scope", scope,
                        "agent_id", "agent-1",
                        "tenant_id", tenant,
                        "task_id", taskId,
                        "audit_id", "audit-1",
                        "credential_type", credentialType,
                        "delegation_depth", depth));
        SecurityContextHolder.getContext().setAuthentication(new JwtAuthenticationToken(jwt));
    }
}
