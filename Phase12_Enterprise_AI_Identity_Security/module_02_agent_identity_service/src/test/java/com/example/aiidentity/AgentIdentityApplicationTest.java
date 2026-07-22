package com.example.aiidentity;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.nimbusds.jwt.SignedJWT;
import java.util.Map;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;

@SpringBootTest
@AutoConfigureMockMvc
class AgentIdentityApplicationTest {
    @Autowired MockMvc mvc;
    @Autowired ObjectMapper objectMapper;

    @Test
    void protectsIdentityManagementAndBrokerEndpoints() throws Exception {
        mvc.perform(post("/agent/register")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{}"))
                .andExpect(status().isUnauthorized());

        mvc.perform(post("/agent/token")
                        .header("X-Identity-Token", "wrong-token")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{}"))
                .andExpect(status().isUnauthorized());
    }

    @Test
    void registersIssuesTaskTokenAndRevokesAgent() throws Exception {
        String registrationBody = objectMapper.writeValueAsString(Map.of(
                "displayName", "Finance Assistant",
                "ownerId", "user-101",
                "tenantId", "fictional-acme",
                "scopes", new String[] {"invoice.read", "invoice.list"}));

        String registrationJson = mvc.perform(post("/agent/register")
                        .header("X-Identity-Token", "local-admin-only")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(registrationBody))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.status").value("ACTIVE"))
                .andReturn().getResponse().getContentAsString();
        String agentId = objectMapper.readTree(registrationJson).get("id").asText();

        String tokenBody = objectMapper.writeValueAsString(Map.of(
                "agentId", agentId,
                "taskId", "task-demo-001",
                "actorId", "user-101",
                "requestedScopes", new String[] {"invoice.read"},
                "audience", "fictional-invoice-api",
                "ttlSeconds", 600,
                "delegationDepth", 0));
        String tokenJson = mvc.perform(post("/agent/task-token")
                        .header("X-Identity-Token", "local-broker-only")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(tokenBody))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.scope").value("invoice.read"))
                .andReturn().getResponse().getContentAsString();

        JsonNode tokenResponse = objectMapper.readTree(tokenJson);
        SignedJWT token = SignedJWT.parse(tokenResponse.get("accessToken").asText());
        assertThat(token.getJWTClaimsSet().getAudience()).containsExactly("fictional-invoice-api");
        assertThat(token.getJWTClaimsSet().getStringClaim("tenant_id")).isEqualTo("fictional-acme");
        assertThat(token.getJWTClaimsSet().getStringClaim("task_id")).isEqualTo("task-demo-001");
        assertThat(token.getHeader().getAlgorithm()).hasToString("RS256");

        mvc.perform(post("/agent/revoke")
                        .header("X-Identity-Token", "local-admin-only")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(Map.of(
                                "agentId", agentId,
                                "reason", "End of fictional demonstration"))))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.status").value("REVOKED"));

        mvc.perform(get("/agent/{id}/status", agentId)
                        .header("X-Identity-Token", "local-status-only"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.active").value(false));

        mvc.perform(post("/agent/task-token")
                        .header("X-Identity-Token", "local-broker-only")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(tokenBody))
                .andExpect(status().isForbidden());
    }

    @Test
    void rejectsScopeEscalationAndInvalidTaskTtl() throws Exception {
        String registrationJson = mvc.perform(post("/agent/register")
                        .header("X-Identity-Token", "local-admin-only")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(Map.of(
                                "displayName", "Read Only Assistant",
                                "ownerId", "user-202",
                                "tenantId", "fictional-globex",
                                "scopes", new String[] {"invoice.read"}))))
                .andExpect(status().isCreated())
                .andReturn().getResponse().getContentAsString();
        String agentId = objectMapper.readTree(registrationJson).get("id").asText();

        mvc.perform(post("/agent/task-token")
                        .header("X-Identity-Token", "local-broker-only")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(Map.of(
                                "agentId", agentId,
                                "taskId", "task-overreach",
                                "actorId", "user-202",
                                "requestedScopes", new String[] {"invoice.approve"},
                                "audience", "fictional-invoice-api",
                                "ttlSeconds", 600))))
                .andExpect(status().isForbidden())
                .andExpect(jsonPath("$.error").value("Requested scopes exceed the agent allow-list"));

        mvc.perform(post("/agent/task-token")
                        .header("X-Identity-Token", "local-broker-only")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(Map.of(
                                "agentId", agentId,
                                "taskId", "task-too-long",
                                "actorId", "user-202",
                                "requestedScopes", new String[] {"invoice.read"},
                                "audience", "fictional-invoice-api",
                                "ttlSeconds", 601))))
                .andExpect(status().isBadRequest());
    }

    @Test
    void publishesOnlyPublicJwkMaterial() throws Exception {
        String jwks = mvc.perform(get("/.well-known/jwks.json"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.keys[0].kty").value("RSA"))
                .andExpect(jsonPath("$.keys[0].kid").value("phase12-local-key"))
                .andReturn().getResponse().getContentAsString();
        assertThat(jwks).doesNotContain("\"d\"");
    }
}
