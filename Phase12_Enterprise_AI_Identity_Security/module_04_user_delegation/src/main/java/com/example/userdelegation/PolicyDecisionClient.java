package com.example.userdelegation;

import java.util.Map;
import java.util.Set;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;
import org.springframework.web.server.ResponseStatusException;

@Component
class PolicyDecisionClient {
    private final RestClient client;
    private final boolean remotePolicyEnabled;

    PolicyDecisionClient(
            RestClient.Builder builder,
            @Value("${policy.decision-url:}") String decisionUrl) {
        this.remotePolicyEnabled = decisionUrl != null && !decisionUrl.isBlank();
        this.client = remotePolicyEnabled ? builder.baseUrl(decisionUrl).build() : builder.build();
    }

    void authorize(
            Map<String, Object> userClaims,
            Set<String> scopes,
            String agentTenant,
            String audience) {
        String userTenant = userClaims.get("tenant_id") == null
                ? null
                : userClaims.get("tenant_id").toString();
        if (userTenant == null || !userTenant.equals(agentTenant)) {
            throw new ResponseStatusException(
                    HttpStatus.FORBIDDEN,
                    "User and agent tenant must match");
        }
        if (!remotePolicyEnabled) return;

        Map<String, Object> input = Map.of(
                "input", Map.of(
                        "user_tenant", userTenant,
                        "agent_tenant", agentTenant,
                        "requested_scopes", scopes,
                        "audience", audience));
        Map<?, ?> response;
        try {
            response = client.post().body(input).retrieve().body(Map.class);
        } catch (RuntimeException exception) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "Policy engine is unavailable");
        }
        Object resultObject = response == null ? null : response.get("result");
        boolean allowed = resultObject instanceof Map<?, ?> result
                && Boolean.TRUE.equals(result.get("allow"));
        if (!allowed) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "Policy engine denied delegation");
        }
    }
}
