package com.example.userdelegation;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.NotNull;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.core.oidc.user.OidcUser;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.client.RestClient;

@RestController
class DelegationController {
    private final DelegationPolicy policy;
    private final PolicyDecisionClient policyDecisionClient;
    private final RestClient identityStatusClient;
    private final RestClient identityBrokerClient;

    DelegationController(
            DelegationPolicy policy,
            PolicyDecisionClient policyDecisionClient,
            RestClient.Builder builder,
            @Value("${identity.base-url}") String identityBaseUrl,
            @Value("${identity.broker-token}") String brokerToken,
            @Value("${identity.status-token}") String statusToken) {
        this.policy = policy;
        this.policyDecisionClient = policyDecisionClient;
        this.identityStatusClient = builder.clone()
                .baseUrl(identityBaseUrl)
                .defaultHeader("X-Identity-Token", statusToken)
                .build();
        this.identityBrokerClient = builder.clone()
                .baseUrl(identityBaseUrl)
                .defaultHeader("X-Identity-Token", brokerToken)
                .build();
    }

    @GetMapping("/")
    Map<String, Object> home() {
        return Map.of(
                "module", "Phase 12 user delegation",
                "login", "/delegation/context",
                "rule", "The user and agent must both allow every delegated scope");
    }

    @GetMapping("/delegation/context")
    Map<String, Object> context(@AuthenticationPrincipal OidcUser user) {
        return Map.of(
                "userSubject", user.getSubject(),
                "delegableScopes", policy.delegableScopes(user.getClaims()),
                "tenant", user.getClaimAsString("tenant_id") == null
                        ? "read tenant_id from the access-token mapping in the capstone"
                        : user.getClaimAsString("tenant_id"));
    }

    @PostMapping("/delegation/request")
    Map<?, ?> delegate(
            @AuthenticationPrincipal OidcUser user,
            @Valid @RequestBody DelegationRequest request) {
        Set<String> scopes = policy.authorize(user.getClaims(), request.requestedScopes());
        Map<?, ?> agent = identityStatusClient.get()
                .uri("/agent/{id}", request.agentId())
                .retrieve()
                .body(Map.class);
        String agentTenant = agent == null || agent.get("tenantId") == null
                ? null
                : agent.get("tenantId").toString();
        policyDecisionClient.authorize(user.getClaims(), scopes, agentTenant, request.audience());
        Map<String, Object> brokerRequest = Map.of(
                "agentId", request.agentId(),
                "taskId", request.taskId(),
                "actorId", "user:" + user.getSubject(),
                "requestedScopes", scopes,
                "audience", request.audience(),
                "ttlSeconds", 600,
                "delegationDepth", 0);
        return identityBrokerClient.post()
                .uri("/agent/task-token")
                .body(brokerRequest)
                .retrieve()
                .body(Map.class);
    }

    record DelegationRequest(
            @NotNull UUID agentId,
            @NotBlank String taskId,
            @NotEmpty Set<String> requestedScopes,
            @NotBlank String audience) {}
}
