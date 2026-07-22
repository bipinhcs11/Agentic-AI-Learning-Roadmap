package com.example.aiidentity.service;

import java.time.Duration;
import java.time.Instant;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Component;

@Component
@ConditionalOnProperty(name = "identity.redis.enabled", havingValue = "false", matchIfMissing = true)
class InMemoryTaskStateStore implements TaskStateStore {
    private final Map<String, TaskState> tasks = new ConcurrentHashMap<>();

    @Override
    public void activate(String taskId, UUID agentId, Duration ttl) {
        tasks.compute(taskId, (ignored, existing) -> {
            if (existing != null && existing.expiresAt().isAfter(Instant.now())) {
                throw new IllegalStateException("Task id is already active");
            }
            return new TaskState(agentId, Instant.now().plus(ttl), true);
        });
    }

    @Override
    public boolean isActive(String taskId, UUID agentId) {
        TaskState state = tasks.get(taskId);
        return state != null
                && state.active()
                && state.agentId().equals(agentId)
                && state.expiresAt().isAfter(Instant.now());
    }

    @Override
    public void revoke(String taskId, UUID agentId) {
        tasks.computeIfPresent(taskId, (ignored, existing) ->
                existing.agentId().equals(agentId)
                        ? new TaskState(agentId, existing.expiresAt(), false)
                        : existing);
    }

    private record TaskState(UUID agentId, Instant expiresAt, boolean active) {}
}
