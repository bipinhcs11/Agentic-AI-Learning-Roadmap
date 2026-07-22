package com.example.securemcp;

import java.util.Map;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;

@Component
class IdentityStatusClient implements TaskStatusVerifier {
    private final RestClient client;

    IdentityStatusClient(
            RestClient.Builder builder,
            @Value("${identity.status-base-url}") String identityBaseUrl,
            @Value("${identity.status-token}") String statusToken) {
        this.client = builder
                .baseUrl(identityBaseUrl)
                .defaultHeader("X-Identity-Token", statusToken)
                .build();
    }

    @Override
    public boolean isActive(String agentId, String taskId) {
        try {
            Map<?, ?> agent = client.get()
                    .uri("/agent/{id}/status", agentId)
                    .retrieve()
                    .body(Map.class);
            Map<?, ?> task = client.get()
                    .uri(uriBuilder -> uriBuilder
                            .path("/task/{taskId}/status")
                            .queryParam("agentId", agentId)
                            .build(taskId))
                    .retrieve()
                    .body(Map.class);
            return agent != null && task != null
                    && Boolean.TRUE.equals(agent.get("active"))
                    && Boolean.TRUE.equals(task.get("active"));
        } catch (RuntimeException exception) {
            return false;
        }
    }
}
