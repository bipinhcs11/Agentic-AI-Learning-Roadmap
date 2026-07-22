package com.example.aiidentity.service;

import java.time.Duration;
import java.util.UUID;

public interface TaskStateStore {
    void activate(String taskId, UUID agentId, Duration ttl);
    boolean isActive(String taskId, UUID agentId);
    void revoke(String taskId, UUID agentId);
}
