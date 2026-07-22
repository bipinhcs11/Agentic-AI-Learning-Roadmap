package com.example.taskcredentials;

import java.util.Map;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;

@Component
public class AgentStatusClient {
    private final RestClient restClient;

    public AgentStatusClient(
            RestClient.Builder builder,
            @Value("${identity.status-base-url}") String identityBaseUrl,
            @Value("${identity.status-token}") String statusToken) {
        this.restClient = builder
                .baseUrl(identityBaseUrl)
                .defaultHeader("X-Identity-Token", statusToken)
                .build();
    }

    public boolean isActive(String agentId) {
        try {
            @SuppressWarnings("unchecked")
            Map<String, Object> response = restClient.get()
                    .uri("/agent/{id}/status", agentId)
                    .retrieve()
                    .body(Map.class);
            return response != null && Boolean.TRUE.equals(response.get("active"));
        } catch (RuntimeException exception) {
            return false; // fail closed when revocation state cannot be checked
        }
    }

    public boolean isTaskActive(String taskId, String agentId) {
        try {
            @SuppressWarnings("unchecked")
            Map<String, Object> response = restClient.get()
                    .uri(uriBuilder -> uriBuilder
                            .path("/task/{taskId}/status")
                            .queryParam("agentId", agentId)
                            .build(taskId))
                    .retrieve()
                    .body(Map.class);
            return response != null && Boolean.TRUE.equals(response.get("active"));
        } catch (RuntimeException exception) {
            return false;
        }
    }
}
