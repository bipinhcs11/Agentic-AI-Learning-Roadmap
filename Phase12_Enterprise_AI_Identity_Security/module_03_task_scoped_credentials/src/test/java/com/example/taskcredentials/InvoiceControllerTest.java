package com.example.taskcredentials;

import static org.mockito.Mockito.when;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.jwt;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;

@SpringBootTest
@AutoConfigureMockMvc
class InvoiceControllerTest {
    @Autowired MockMvc mvc;
    @MockitoBean AgentStatusClient agentStatusClient;

    @Test
    void rejectsMissingAuthentication() throws Exception {
        mvc.perform(get("/fictional-invoices/inv-acme-001"))
                .andExpect(status().isUnauthorized());
    }

    @Test
    void allowsNarrowTaskCredentialForSameTenant() throws Exception {
        when(agentStatusClient.isActive("agent-1")).thenReturn(true);
        when(agentStatusClient.isTaskActive("task-001", "agent-1")).thenReturn(true);
        mvc.perform(get("/fictional-invoices/inv-acme-001")
                        .with(jwt()
                                .authorities(() -> "SCOPE_invoice.read")
                                .jwt(token -> token
                                        .claim("credential_type", "task")
                                        .claim("task_id", "task-001")
                                        .claim("agent_id", "agent-1")
                                        .claim("tenant_id", "fictional-acme")
                                        .claim("audit_id", "audit-001"))))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.id").value("inv-acme-001"))
                .andExpect(jsonPath("$.taskId").value("task-001"));
    }

    @Test
    void deniesMissingScope() throws Exception {
        mvc.perform(get("/fictional-invoices/inv-acme-001")
                        .with(jwt().authorities(() -> "SCOPE_invoice.list")))
                .andExpect(status().isForbidden());
    }

    @Test
    void deniesGeneralAgentTokenAndCrossTenantTask() throws Exception {
        mvc.perform(get("/fictional-invoices/inv-acme-001")
                        .with(jwt()
                                .authorities(() -> "SCOPE_invoice.read")
                                .jwt(token -> token.claim("credential_type", "agent"))))
                .andExpect(status().isForbidden());

        mvc.perform(get("/fictional-invoices/inv-globex-001")
                        .with(jwt()
                                .authorities(() -> "SCOPE_invoice.read")
                                .jwt(token -> token
                                        .claim("credential_type", "task")
                                        .claim("task_id", "task-001")
                                        .claim("agent_id", "agent-1")
                                        .claim("tenant_id", "fictional-acme"))))
                .andExpect(status().isForbidden());
    }

    @Test
    void failsClosedWhenAgentIsRevokedOrStatusUnavailable() throws Exception {
        when(agentStatusClient.isActive("agent-revoked")).thenReturn(false);
        mvc.perform(get("/fictional-invoices/inv-acme-001")
                        .with(jwt()
                                .authorities(() -> "SCOPE_invoice.read")
                                .jwt(token -> token
                                        .claim("credential_type", "task")
                                        .claim("task_id", "task-002")
                                        .claim("agent_id", "agent-revoked")
                                        .claim("tenant_id", "fictional-acme"))))
                .andExpect(status().isForbidden());
    }
}
